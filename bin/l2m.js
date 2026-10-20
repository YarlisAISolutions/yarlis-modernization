#!/usr/bin/env node
// l2m: legacy to modern. Analyze legacy code and generate versioned, traceable BRD/FRD/SRD/RTM documents with
// the agent of your choice. Deterministic steps run the bundled Python scripts; writing is done by the agent.
import { parseArgs } from 'node:util';
import { AGENTS, install } from '../lib/install.js';
import { generate } from '../lib/generate.js';
import { doctor } from '../lib/doctor.js';
import { runScript, VERSION } from '../lib/python.js';

const HELP = `l2m ${VERSION}: legacy code → versioned BRD, FRD, SRD and RTM, with Claude Code, Copilot, Codex or Gemini

Usage: l2m <command> [options]

Set up
  init [dir]           Install the skills, the agent kit, l2m.config.json and PROJECT-CONTEXT.md into a repository
                       --agents claude,copilot,codex,gemini  --project <name> --src <path> --owner <name>
                       --target-stack <text>  --force  --upgrade (refresh skills and prompts)  --dry-run
  doctor               Check Node, Python 3.9+, git, the agent CLIs and the installed kit

Deterministic tools (arguments go straight to the bundled scripts; add --help to any of them)
  analyze <cmd> ...    inventory.py: scan | slice | domains | schema-diff
  map ...              mapgen.py: legacy → React / Spring Boot / Spring Batch / DB2 mapping
  docs <cmd> ...       docver.py: init | new-feature | bump | validate | linkify | trace | rtm | status | diff |
                       index | check | bumpcheck

Agent workflow
  generate <step>      Prepare inputs, scaffold, run the agent, then linkify + trace + validate + index
                       steps: analysis | brd | frd | srd | all (brd → frd → srd) | change-request | assess
  prompt <step>        Print the filled prompt instead of running an agent (same options as generate)

generate / prompt options
  --module <m> --feature <f>   Feature folder (kebab-case): <requirementsDir>/<m>/<f>/
  --scope "<slice>"            Transactions, jobs, programs or a description (required for analysis, brd, all)
  --out-of-scope "<text>"      --title "<text>"  --component <c>
  --src <path>                 Source tree (repeatable; overrides "source")
  --docs <path|url>            Extra documents and notes (repeatable; added to "docs")
  --schema <path>              Extra DDL / DCLGEN / migration files (repeatable; added to "schema")
  --agent <name>               claude | copilot | codex | gemini (default: "agent" in l2m.config.json)
  --agent-cmd "<cmd> {prompt}" Any other agent; {prompt} / {prompt_file}, or stdin when neither is used
  --yolo                       Let the agent skip all permission checks (unsafe; off by default)
  --print                      Print the prompt instead of running the agent
  --force                      Regenerate a document that is past 0.1.0
  --no-init                    Fail instead of running \`l2m init\` when there is no l2m.config.json
  change-request: --cr <ID> --summary "<change>" [--schema-diff <base>[..<head>]] [--affects "BRD, FRD"]
                  [--requested-by <name>] [--reason <text>] [--refs <links>] [--author <name>]

Examples
  npx @l2m/cli init --src legacy/app --project "Card Demo"
  l2m analyze scan --src legacy/app --out docs/analysis
  l2m generate brd --module user-admin --feature sign-on --scope "CC00, CU00-CU03" --agent claude
  l2m generate all --module accounts --feature account-update --scope "AU01" --agent codex
  l2m generate change-request --module accounts --feature account-update --cr CR-007 \\
      --summary "Track the last transaction time on accounts" --schema-diff origin/main
  l2m prompt frd --module accounts --feature account-update > frd-prompt.md

Docs: https://github.com/YarlisAISolutions/yarlis-modernization`;

const GEN_OPTIONS = {
  module: { type: 'string' }, feature: { type: 'string' }, component: { type: 'string' }, title: { type: 'string' },
  scope: { type: 'string' }, 'out-of-scope': { type: 'string' },
  src: { type: 'string', multiple: true }, docs: { type: 'string', multiple: true }, schema: { type: 'string', multiple: true },
  agent: { type: 'string' }, 'agent-cmd': { type: 'string' }, yolo: { type: 'boolean' }, print: { type: 'boolean' },
  force: { type: 'boolean' }, 'no-init': { type: 'boolean' },
  cr: { type: 'string' }, summary: { type: 'string' }, 'schema-diff': { type: 'string' }, affects: { type: 'string' },
  'requested-by': { type: 'string' }, reason: { type: 'string' }, refs: { type: 'string' }, author: { type: 'string' },
};

function main(argv) {
  const [cmd, ...rest] = argv;
  switch (cmd) {
    case undefined: case '-h': case '--help': case 'help':
      console.log(HELP); return 0;
    case '-v': case '--version': case 'version':
      console.log(VERSION); return 0;
    case 'analyze': return runScript('inventory', rest);
    case 'map': return runScript('mapgen', rest);
    case 'docs': return runScript('docver', rest);
    case 'doctor': return doctor();
    case 'init': {
      const { values: v, positionals } = parseArgs({ args: rest, allowPositionals: true, options: {
        agents: { type: 'string' }, project: { type: 'string' }, src: { type: 'string' }, owner: { type: 'string' },
        'target-stack': { type: 'string' }, force: { type: 'boolean' }, upgrade: { type: 'boolean' }, 'dry-run': { type: 'boolean' },
      } });
      install(positionals[0] || '.', {
        agents: v.agents ? v.agents.split(',').map((s) => s.trim()).filter(Boolean) : AGENTS,
        project: v.project, src: v.src, owner: v.owner, targetStack: v['target-stack'],
        force: v.force, upgrade: v.upgrade, dryRun: v['dry-run'],
      });
      return 0;
    }
    case 'generate': case 'prompt': {
      const { values: v, positionals } = parseArgs({ args: rest, allowPositionals: true, options: GEN_OPTIONS });
      if (!positionals[0]) throw Object.assign(new Error(`usage: l2m ${cmd} <analysis|brd|frd|srd|all|change-request|assess> [options]`), { exitCode: 2 });
      // Status goes to stderr so `l2m prompt brd ... > prompt.md` captures only the prompt.
      return generate(positionals[0], { ...v, print: cmd === 'prompt' || v.print }, console.error);
    }
    default:
      throw Object.assign(new Error(`unknown command "${cmd}"; see l2m --help`), { exitCode: 2 });
  }
}

try {
  process.exitCode = main(process.argv.slice(2));
} catch (e) {
  console.error(`l2m: ${e.message}`);
  process.exitCode = e.exitCode || (e.code?.startsWith?.('ERR_PARSE_ARGS') ? 2 : 1);
}
