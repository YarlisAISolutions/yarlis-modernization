// Build the prompt for one step from prompts/0N-*.md. The template's Role, Deliverables, Rules and Verification
// blocks are kept word for word (they are the standard); Context, Task, Scope and Inputs are filled from the
// config, the flags and the documents already on disk.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { PKG_ROOT } from './python.js';

export const STEPS = {
  analysis: '01-analyze-legacy-code.md',
  brd: '02-generate-brd.md',
  frd: '03-generate-frd.md',
  srd: '04-generate-srd.md',
  'change-request': '05-change-request.md',
  assess: '06-implementation-assessment.md',
};

const PLACEHOLDER = /\[[A-Z][A-Z0-9 _/.,|-]*[A-Z0-9]\](?!\()/g;

/** { n: { title, body } } from the template's fenced markdown block. */
export function templateSections(step) {
  const text = readFileSync(join(PKG_ROOT, 'prompts', STEPS[step]), 'utf8');
  const block = text.match(/```markdown\n([\s\S]*?)\n```/);
  if (!block) throw new Error(`prompts/${STEPS[step]} has no markdown block`);
  const out = {};
  for (const m of block[1].matchAll(/^## (\d+)\. (.+)\n([\s\S]*?)(?=^## \d+\. |(?![\s\S]))/gm)) {
    out[m[1]] = { title: m[2].trim(), body: m[3].trim() };
  }
  return out;
}

const bullets = (items) => items.filter(Boolean).map((i) => `- ${i}`).join('\n');

/**
 * ctx: { cfg, featureDir, module, feature, scope, outOfScope, versions: {BRD, FRD, SRD}, cr, summary, author,
 *        requestedBy, reason, refs, inputsPath, schemaDiffPath, sources, git: { url, sha }, date, affects }
 */
export function buildPrompt(step, ctx) {
  const t = templateSections(step);
  const { cfg, featureDir: dir } = ctx;
  const v = (k) => ctx.versions?.[k] || 'not created yet';
  const subst = (s) => s
    .replaceAll('docs/requirements/<module>/<feature>', dir || `${cfg.requirementsDir}/<module>/<feature>`)
    .replaceAll('<module>', ctx.module || '<module>')
    .replaceAll('<feature>', ctx.feature || '<feature>')
    .replaceAll('docs/requirements', cfg.requirementsDir)
    .replaceAll('docs/analysis', cfg.analysisDir)
    .replaceAll('[PROJECT]', cfg.project)
    .replaceAll('[CR-ID]', ctx.cr || '[CR-ID]')
    .replaceAll('[NAME]', ctx.author || '[NAME]');

  const context = [`See ${cfg.requirementsDir}/PROJECT-CONTEXT.md. Project: ${cfg.project}; business owner: ${cfg.owner}.`,
    `Target stack: ${cfg.targetStack}.`];
  if (step === 'assess') context.push(`Assessment date: ${ctx.date}; repository: ${ctx.git?.url || 'Unknown'}; commit: ${ctx.git?.sha || 'Unknown'}.`);

  const task = {
    analysis: `Analyze the existing code for ${ctx.scope} and build the analysis knowledge base.`,
    brd: `Write the Business Requirements Document for ${ctx.title} (module ${ctx.module}, feature ${ctx.feature}) in ${dir}/BRD.md, version ${v('BRD')}.`,
    frd: `Derive the Functional Requirements Document in ${dir}/FRD.md from ${dir}/BRD.md (version ${v('BRD')}).`,
    srd: `Derive the System Requirements Document in ${dir}/SRD.md from FRD.md ${v('FRD')} and BRD.md ${v('BRD')}, including the legacy-to-target design.`,
    'change-request': `Change request ${ctx.cr}: ${ctx.summary}.`,
    assess: `Assess how much of the requirements in ${dir} (BRD ${v('BRD')}, FRD ${v('FRD')}, SRD ${v('SRD')}) are implemented, verified and deployed in the codebase at ${ctx.git?.sha || 'HEAD'}.`,
  }[step];

  const scopeLine = ctx.scope ? `Slice: ${ctx.scope}` : null;
  const outLine = ctx.outOfScope ? `Out of scope: ${ctx.outOfScope}` : null;
  const scope = {
    analysis: bullets([scopeLine, outLine]),
    brd: bullets([scopeLine, outLine]),
    frd: bullets([ctx.scope ? scopeLine : 'Same slice as the BRD.', outLine]),
    srd: bullets([ctx.scope ? scopeLine : 'Same slice as the FRD.', outLine, `Migration strategy constraints: ${cfg.migrationStrategy}.`]),
    'change-request': bullets([`Documents affected: ${ctx.affects}. Carry the change downstream to every affected document.`, scopeLine, outLine]),
    assess: bullets([ctx.scope ? scopeLine : 'All requirements in the documents (BR, RUL, FR, SR, NFR, IFR, DR).', outLine]),
  }[step];

  const sources = ctx.sources?.length ? ctx.sources.join(', ') : 'none given';
  const common = [
    `Source tree: ${sources}`,
    step !== 'analysis' ? `Analysis knowledge base: ${cfg.analysisDir}/ (inventory.md, program cards, crud-matrix.md, data-dictionary.md, screens.md, batch-flows.md, rules, findings)` : null,
    `Existing documents, notes and schema files: ${ctx.inputsPath} (paths and checksums; read the files it lists)`,
  ];
  const inputs = bullets({
    analysis: common,
    brd: common,
    frd: [`${dir}/BRD.md`, ...common],
    srd: [`${dir}/FRD.md`, `${dir}/BRD.md`, `${cfg.analysisDir}/target-mapping.md and data-mapping.md (mapgen drafts)`, ...common],
    'change-request': [
      `Requested by ${ctx.requestedBy || 'Unknown'}; reason: ${ctx.reason || 'Unknown'}; references: ${ctx.refs || 'none'}`,
      ctx.schemaDiffPath ? `Schema changes with the affected programs and requirement IDs: ${ctx.schemaDiffPath}` : null,
      ...common],
    assess: [...common, 'Configuration, migrations, API definitions, UI, tests and results, CI/CD workflows and runs, deployment configuration and release notes in this repository. Artifacts not available: none listed.'],
  }[step]);

  const preface = [
    `Use the Agent Skills in .claude/skills (legacy-code-analysis, requirements-docs, mainframe-modernization) and follow them exactly.`,
    `Run their scripts with python3, e.g. \`python3 .claude/skills/requirements-docs/scripts/docver.py validate ${dir || cfg.requirementsDir}\`.`,
    `Inputs are given as paths and links: read them, cite them as path:line links, never paste their content.`,
  ].join('\n');

  const verification = `${subst(t[8].body)}\nWhen you finish, l2m runs linkify, trace --inject, validate and index again and fails the run on validation errors.`;
  const prompt = [
    preface,
    `## 1. ${t[1].title}\n${subst(t[1].body)}`,
    `## 2. Context\n${context.join('\n')}`,
    `## 3. Task\n${task}`,
    `## 4. Scope\n${scope || '- As stated in the task.'}`,
    `## 5. Inputs\n${inputs}`,
    `## 6. ${t[6].title}\n${subst(t[6].body)}`,
    `## 7. ${t[7].title}\n${subst(t[7].body)}`,
    `## 8. ${t[8].title}\n${verification}`,
  ].join('\n\n');

  const left = [...new Set(prompt.match(PLACEHOLDER) || [])];
  if (left.length) throw new Error(`the ${step} prompt still has placeholders ${left.join(', ')}; pass the matching flags`);
  return `${prompt}\n`;
}
