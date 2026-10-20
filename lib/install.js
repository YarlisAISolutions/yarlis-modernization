// `l2m init`: install the skills and the agent kit into a repository (the Node port of scripts/install.sh).
// Existing files are kept unless --force; copilot-instructions.md, AGENTS.md and GEMINI.md get a marked section
// appended instead. --upgrade replaces only the files l2m owns: the skills and prompts/.
import { appendFileSync, cpSync, existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import { PKG_ROOT, VERSION, runScript } from './python.js';
import { CONFIG_FILE, defaultConfig } from './config.js';

export const SKILLS = ['legacy-code-analysis', 'requirements-docs', 'mainframe-modernization'];
export const AGENTS = ['claude', 'copilot', 'codex', 'gemini'];
const BEGIN = '<!-- yarlis-modernization:begin -->';
const END = '<!-- yarlis-modernization:end -->';

const COPILOT_FILES = [
  'instructions/requirements-docs.instructions.md', 'instructions/legacy-analysis.instructions.md',
  'prompts/new-feature-requirements.prompt.md', 'prompts/analyze-legacy.prompt.md',
  'prompts/change-request.prompt.md', 'prompts/assess-implementation.prompt.md',
  'agents/requirements-analyst.agent.md', 'ISSUE_TEMPLATE/feature-requirements.yml', 'pull_request_template.md',
].map((f) => `.github/${f}`);

const skipCache = (src) => !/(^|[\\/])(__pycache__|.*\.pyc)$/.test(src);

/** The file plan for the chosen agents: [{ action: 'copy'|'append', rel, dst, managed }]. */
export function plan(agents) {
  const items = [];
  for (const s of SKILLS) items.push({ action: 'copy', rel: `.claude/skills/${s}`, managed: true });
  items.push({ action: 'copy', rel: 'prompts', managed: true });
  items.push({ action: 'copy', rel: '.github/workflows/requirements-check.yml' });
  if (agents.includes('copilot')) {
    items.push({ action: 'append', rel: '.github/copilot-instructions.md' });
    for (const f of COPILOT_FILES) items.push({ action: 'copy', rel: f });
    items.push({ action: 'copy', rel: '.github/workflows/copilot-setup-steps.yml' });
  }
  if (agents.some((a) => a !== 'claude')) items.push({ action: 'append', rel: 'AGENTS.md' });
  if (agents.includes('gemini')) items.push({ action: 'append', rel: 'AGENTS.md', dst: 'GEMINI.md' });
  return items;
}

export function install(target, { agents = AGENTS, force = false, dryRun = false, upgrade = false,
  project, src, owner, targetStack, log = console.log } = {}) {
  target = resolve(target);
  if (!existsSync(target) || !statSync(target).isDirectory()) throw new Error(`${target} is not a directory`);
  if (resolve(target) === resolve(PKG_ROOT)) throw new Error('target is the l2m package itself');
  const bad = agents.filter((a) => !AGENTS.includes(a));
  if (bad.length) throw new Error(`unknown agent(s) ${bad.join(', ')}; choose from ${AGENTS.join(', ')}`);
  const act = (msg, fn) => { if (dryRun) log(`would: ${msg}`); else fn(); };

  for (const { action, rel, dst = rel, managed } of plan(agents)) {
    const to = join(target, dst);
    const from = join(PKG_ROOT, rel);
    if (action === 'append') {
      const section = `${BEGIN}\n${readFileSync(from, 'utf8')}${END}\n`;
      // A new file gets the markers too, so the next run sees the section and doesn't append it again.
      if (!existsSync(to)) { act(`write ${dst}`, () => { mkdirSync(dirname(to), { recursive: true }); writeFileSync(to, section); }); log(`add      ${dst}`); continue; }
      if (readFileSync(to, 'utf8').includes(BEGIN)) { log(`keep     ${dst} (section already present)`); continue; }
      act(`append section to ${dst}`, () => appendFileSync(to, `\n${section}`));
      log(`append   ${dst}`);
      continue;
    }
    const replace = force || (upgrade && managed);
    const existed = existsSync(to);
    if (existed && !replace) {
      const hint = dst.endsWith('copilot-setup-steps.yml') ? 'exists: add Node, Python 3 and fetch-depth: 0 by hand' : 'exists; --force to replace';
      log(`keep     ${dst} (${hint})`);
      continue;
    }
    act(`copy ${dst}`, () => {
      if (existed) rmSync(to, { recursive: true, force: true });
      cpSync(from, to, { recursive: true, filter: skipCache });
    });
    log(`${existed ? 'update  ' : 'add     '} ${dst}`);
  }

  for (const d of ['docs/requirements', 'docs/inputs']) act(`mkdir ${d}`, () => mkdirSync(join(target, d), { recursive: true }));
  act('write .claude/skills/.l2m-version', () => writeFileSync(join(target, '.claude/skills/.l2m-version'), `${VERSION}\n`));

  const cfgPath = join(target, CONFIG_FILE);
  if (existsSync(cfgPath)) log(`keep     ${CONFIG_FILE}`);
  else {
    const cfg = defaultConfig({ project: project || basename(target), src, owner, targetStack, agent: agents[0] });
    act(`write ${CONFIG_FILE}`, () => writeFileSync(cfgPath, `${JSON.stringify(cfg, null, 2)}\n`));
    log(`add      ${CONFIG_FILE}`);
  }

  if (!existsSync(join(target, 'docs/requirements/PROJECT-CONTEXT.md'))) {
    const args = ['init', '--type', 'context', '--dir', 'docs/requirements', '--project', project || basename(target)];
    if (owner) args.push('--owner', owner);
    if (targetStack) args.push('--target-stack', targetStack);
    if (src) args.push('--src', src);
    act('docver.py init --type context', () => {
      if (runScript('docver', args, { cwd: target, quiet: true }) !== 0) throw new Error('docver.py init --type context failed');
    });
    log('add      docs/requirements/PROJECT-CONTEXT.md');
  }

  log(`
Done (l2m ${VERSION}). Next steps in ${target}:
  1. Fill docs/requirements/PROJECT-CONTEXT.md (owner, users, constraints; Unknown where unknown)
     and l2m.config.json ("source", "docs", "schema", "targetStack", "agent").
  2. Put existing documents, interview notes and specs in docs/inputs/.
  3. l2m analyze scan --src <legacy-source> --out docs/analysis
  4. l2m generate brd --module <m> --feature <f> --scope "<transactions, jobs or description>"
     then: l2m generate frd ... and l2m generate srd ... (or: l2m generate all ...)
  5. Commit on a branch and open a PR: CI runs docver.py check and bumpcheck.`);
}
