// `l2m generate <step>`: the deterministic steps around an agent run.
//   preflight (config, kit, fresh analysis, inputs manifest) → scaffold → prompt → agent (or --print) → post-check.
// The post-check is run by l2m, not trusted to the agent: linkify, trace --inject, validate, index.
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { AGENTS as KIT_AGENTS, install } from './install.js';
import { findConfig, validateConfig } from './config.js';
import { needsScan, writeManifest } from './inputs.js';
import { buildPrompt, STEPS } from './prompts.js';
import { available, resolveAgent, runAgent } from './agents.js';
import { captureScript, runScript } from './python.js';

const DOCS = { brd: 'BRD', frd: 'FRD', srd: 'SRD' };
const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

const err = (msg) => Object.assign(new Error(msg), { exitCode: 2 });

function version(path) {
  if (!existsSync(path)) return null;
  return readFileSync(path, 'utf8').match(/^version:\s*([0-9.]+)/m)?.[1] || null;
}

function git(cwd, ...args) {
  const r = spawnSync('git', ['-C', cwd, ...args], { encoding: 'utf8' });
  return r.status === 0 ? r.stdout.trim() : '';
}

/** What the kit must contain for an agent to find the skills and rules. */
function entryPoints(agent) {
  return { claude: ['.claude/skills/requirements-docs/SKILL.md'], copilot: ['.claude/skills/requirements-docs/SKILL.md', '.github/copilot-instructions.md'],
    codex: ['AGENTS.md'], gemini: ['GEMINI.md'] }[agent] || [];
}

export function generate(step, o, log = console.log) {
  if (step !== 'all' && !STEPS[step]) throw err(`unknown step "${step}"; use ${[...Object.keys(STEPS), 'all'].join(', ')}`);
  const cwd = process.cwd();

  // Preflight: config (init on first use), kit for the chosen agent.
  let found = findConfig(cwd);
  if (!found) {
    if (o['no-init']) throw err('no l2m.config.json here or above; run `l2m init` first');
    log('No l2m.config.json found: running `l2m init` here first.\n');
    install(cwd, { agents: o.agent && KIT_AGENTS.includes(o.agent) ? [o.agent] : KIT_AGENTS, src: o.src?.[0], log });
    found = findConfig(cwd);
  }
  const root = found.root;
  const cfg = validateConfig({
    ...found.config,
    ...(o.src ? { source: o.src } : {}),
    ...(o.docs ? { docs: [...found.config.docs, ...o.docs] } : {}),
    ...(o.schema ? { schema: [...found.config.schema, ...o.schema] } : {}),
  });
  const agentName = o['agent-cmd'] ? 'cmd' : o.agent || cfg.agent;
  const print = Boolean(o.print);
  if (!print) {
    for (const p of entryPoints(agentName)) {
      if (!existsSync(join(root, p))) throw err(`${p} is missing, so ${agentName} can't find the skills; run \`l2m init --agents ${agentName}\``);
    }
  }

  const steps = step === 'all' ? ['brd', 'frd', 'srd'] : [step];
  const needsFeature = step !== 'analysis';
  if (needsFeature) {
    for (const k of ['module', 'feature']) {
      if (!o[k]) throw err(`--${k} is required for ${step}`);
      if (!SLUG.test(o[k])) throw err(`--${k} must be kebab-case, e.g. account-update`);
    }
  }
  if (['analysis', 'brd', 'all'].includes(step) && !o.scope) throw err(`--scope is required for ${step} (transactions, jobs, programs or a description)`);
  if (step === 'change-request' && (!o.cr || !o.summary)) throw err('change-request needs --cr <ID> and --summary "<one-sentence change>"');

  // Analysis: rescan the first source tree when it changed since the last scan.
  const analysisDir = resolve(root, cfg.analysisDir);
  const inventory = join(analysisDir, 'inventory.json');
  const src = cfg.source[0] ? resolve(root, cfg.source[0]) : null;
  if (src && !existsSync(src)) throw err(`source ${cfg.source[0]} does not exist`);
  if (src && (step === 'analysis' || needsScan(src, inventory))) {
    log(`Scanning ${cfg.source[0]} → ${cfg.analysisDir}/`);
    if (runScript('inventory', ['scan', '--src', src, '--out', analysisDir], { cwd: root, quiet: true }) !== 0) throw err('inventory.py scan failed');
  } else if (!src && !existsSync(inventory)) {
    log('No source configured ("source" in l2m.config.json or --src): the agent works from documents and notes only.');
  }
  if (steps.includes('srd') && existsSync(inventory) && !existsSync(join(analysisDir, 'target-mapping.md'))) {
    runScript('mapgen', ['--inventory', inventory], { cwd: root, quiet: true });
  }
  const manifest = writeManifest(cfg, root);
  const missing = manifest.rows.filter((r) => r.kind === 'missing');
  if (missing.length) log(`Warning: inputs not found: ${missing.map((r) => r.ref).join(', ')}`);

  // Scaffold the feature folder and the project context.
  const reqDir = resolve(root, cfg.requirementsDir);
  const featureRel = needsFeature ? `${cfg.requirementsDir}/${o.module}/${o.feature}` : null;
  const featureDir = featureRel && resolve(root, featureRel);
  if (!existsSync(join(reqDir, 'PROJECT-CONTEXT.md'))) {
    const args = ['init', '--type', 'context', '--dir', cfg.requirementsDir, '--project', cfg.project, '--owner', cfg.owner, '--target-stack', cfg.targetStack];
    if (src) args.push('--src', src);
    runScript('docver', args, { cwd: root, quiet: true });
  }
  if (needsFeature && !existsSync(join(featureDir, 'BRD.md'))) {
    const args = ['new-feature', '--module', o.module, '--feature', o.feature, '--root', cfg.requirementsDir];
    if (o.component) args.push('--component', o.component);
    if (runScript('docver', args, { cwd: root, quiet: true }) !== 0) throw err('docver.py new-feature failed');
    log(`Scaffolded ${featureRel}/ (BRD, FRD, SRD)`);
  }
  if (step === 'assess' && !existsSync(join(featureDir, 'RTM.md'))) {
    runScript('docver', ['new-feature', '--module', o.module, '--feature', o.feature, '--root', cfg.requirementsDir, '--docs', 'rtm,gap'], { cwd: root, quiet: true });
  }

  // Schema changes → a report the change request links to.
  let schemaDiffPath = null;
  if (o['schema-diff']) {
    if (!src) throw err('--schema-diff needs a source tree ("source" or --src) inside a git repository');
    const [base, head] = o['schema-diff'].split('..');
    const out = join(analysisDir, `schema-diff-${`${base}-${head || 'worktree'}`.replace(/[^A-Za-z0-9._-]+/g, '_')}.md`);
    const args = ['schema-diff', '--src', src, '--base', base, '--inventory', inventory, '--requirements', reqDir, '--out', out];
    if (head) args.push('--head', head);
    const r = captureScript('inventory', args, { cwd: root });
    if (r.status !== 0) throw err(`inventory.py schema-diff failed: ${r.stderr.trim()}`);
    log(r.stdout.trim());
    schemaDiffPath = relative(root, out).split('\\').join('/');
  }

  const agent = print ? null : resolveAgent(agentName, { cfg, agentCmd: o['agent-cmd'], yolo: o.yolo });
  if (agent && !available(agent.cmd)) {
    log(`${agent.cmd[0]} is not installed or not on PATH: printing the prompt instead.\n`);
  }
  const live = agent && available(agent.cmd);

  let rc = 0;
  for (const s of steps) {
    const versions = needsFeature ? Object.fromEntries(Object.values(DOCS).map((d) => [d, version(join(featureDir, `${d}.md`))])) : {};
    if (DOCS[s] && versions[DOCS[s]] && versions[DOCS[s]] !== '0.1.0' && !o.force) {
      throw err(`${featureRel}/${DOCS[s]}.md is already at ${versions[DOCS[s]]}; use \`l2m generate change-request\` (or --force to regenerate)`);
    }
    const prompt = buildPrompt(s, {
      cfg, featureDir: featureRel, module: o.module, feature: o.feature, title: o.title || (o.feature && o.feature[0].toUpperCase() + o.feature.slice(1).replaceAll('-', ' ')),
      scope: o.scope, outOfScope: o['out-of-scope'], versions, cr: o.cr, summary: o.summary, author: o.author || cfg.owner,
      requestedBy: o['requested-by'], reason: o.reason, refs: o.refs, schemaDiffPath,
      affects: o.affects || 'BRD, FRD, SRD (and RTM if present)', inputsPath: relative(root, manifest.path).split('\\').join('/'),
      sources: cfg.source, git: { url: git(root, 'remote', 'get-url', 'origin'), sha: git(root, 'rev-parse', 'HEAD') },
      date: new Date().toISOString().slice(0, 10),
    });
    if (!live) {
      process.stdout.write(prompt);
      if (needsFeature) log(`\nThen run: l2m docs linkify ${featureRel} && l2m docs trace ${featureRel} --inject && l2m docs validate ${featureRel} && l2m docs index ${cfg.requirementsDir}`);
      continue;
    }
    log(`\n▶ ${s}: running ${agent.name}${o.yolo ? ' (all permissions skipped: --yolo)' : ''} in ${root}`);
    const code = runAgent(agent, prompt, { cwd: root });
    if (code !== 0) { log(`${agent.name} exited with ${code}`); return code; }
    rc = needsFeature ? postCheck(root, cfg, featureRel, DOCS[s] ? `${featureRel}/${DOCS[s]}.md` : featureRel, log) : 0;
    if (rc !== 0) { log(`\n✗ ${s}: validation failed; fix the errors above (or re-run the step) before the next document.`); return rc; }
  }
  return rc;
}

/** linkify → trace --inject → validate (the generated document, or the whole folder) → index. Returns validate's exit code. */
export function postCheck(root, cfg, featureRel, target, log = console.log) {
  log(`\nPost-check ${target}`);
  runScript('docver', ['linkify', featureRel], { cwd: root, quiet: true });
  runScript('docver', ['trace', featureRel, '--inject'], { cwd: root, quiet: true });
  const rc = runScript('docver', ['validate', target], { cwd: root });
  runScript('docver', ['index', cfg.requirementsDir], { cwd: root, quiet: true });
  runScript('docver', ['status', featureRel], { cwd: root });
  return rc;
}
