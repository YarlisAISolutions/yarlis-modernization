// The l2m 1.0 contract (MOD-3): commands, generate steps, flags, config keys and exit codes, each stable or
// experimental in test/cli-contract.json and docs/cli.md. A stable item may not be removed, renamed or change type
// before 2.0, and nothing new ships without being classified. `l2m --help` and l2m.config.schema.json are
// snapshotted in test/snapshots/; after an announced change, refresh them with:
//   L2M_UPDATE_SNAPSHOTS=1 npm test
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { after, before, describe, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { COMMANDS, GEN_OPTIONS, HELP, INIT_OPTIONS } from '../lib/cli.js';
import { defaultConfig } from '../lib/config.js';
import { STEPS } from '../lib/prompts.js';
import { findPython, VERSION } from '../lib/python.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const BIN = join(ROOT, 'bin/l2m.js');
const CONTRACT = JSON.parse(readFileSync(join(ROOT, 'test/cli-contract.json'), 'utf8'));
const SCHEMA = JSON.parse(readFileSync(join(ROOT, 'l2m.config.schema.json'), 'utf8'));
const UPDATE = process.env.L2M_UPDATE_SNAPSHOTS === '1';
const HOW = 'If the change is intended, update test/cli-contract.json and docs/cli.md (a stable item only in a major release).';

const l2m = (cwd, args, env = process.env) => spawnSync(process.execPath, [BIN, ...args], { cwd, encoding: 'utf8', env: { ...env, NO_COLOR: '1' } });

/** Compare text with test/snapshots/<name>, or write it when L2M_UPDATE_SNAPSHOTS=1. */
function snapshot(name, text) {
  const file = join(ROOT, 'test/snapshots', name);
  if (UPDATE) return writeFileSync(file, text);
  assert.equal(text, readFileSync(file, 'utf8'),
    `${name} changed. Announce the change in docs/cli.md (Contract changes), then run L2M_UPDATE_SNAPSHOTS=1 npm test.`);
}

const tables = { init: INIT_OPTIONS, generate: GEN_OPTIONS };

let W;
before(() => { W = mkdtempSync(join(process.env.L2M_TEST_TMP || tmpdir(), 'l2m-contract-')); });
after(() => rmSync(W, { recursive: true, force: true }));

describe('l2m 1.0 contract', () => {
  test('stable flags keep their names and types', () => {
    const problems = [];
    for (const [cmd, flags] of Object.entries(CONTRACT.flags)) {
      for (const [flag, want] of Object.entries(flags)) {
        const have = tables[cmd][flag.slice(2)];
        if (want.status !== 'stable') continue;
        if (!have) problems.push(`stable flag ${flag} of l2m ${cmd} was removed or renamed`);
        else if (have.type !== want.type || Boolean(have.multiple) !== Boolean(want.multiple)) {
          problems.push(`stable flag ${flag} of l2m ${cmd} changed from ${want.type}${want.multiple ? ' (repeatable)' : ''} to ${have.type}${have.multiple ? ' (repeatable)' : ''}`);
        }
      }
    }
    assert.deepEqual(problems, [], HOW);
  });

  test('every flag is classified', () => {
    const missing = [];
    for (const [cmd, table] of Object.entries(tables)) {
      for (const name of Object.keys(table)) if (!CONTRACT.flags[cmd][`--${name}`]) missing.push(`--${name} of l2m ${cmd}`);
    }
    assert.deepEqual(missing, [], 'add these to test/cli-contract.json and docs/cli.md as stable or experimental');
  });

  test('commands and aliases are dispatched, and every command is classified', () => {
    const contract = [...Object.keys(CONTRACT.commands), ...Object.keys(CONTRACT.aliases)];
    const gone = Object.entries(CONTRACT.commands).filter(([c, s]) => s === 'stable' && !COMMANDS.includes(c)).map(([c]) => c);
    gone.push(...Object.keys(CONTRACT.aliases).filter((a) => !COMMANDS.includes(a)));
    assert.deepEqual(gone, [], `stable commands or aliases removed or renamed. ${HOW}`);
    assert.deepEqual(COMMANDS.filter((c) => !contract.includes(c)), [], 'classify new commands in test/cli-contract.json and docs/cli.md');
    for (const c of Object.keys(CONTRACT.commands)) {
      if (!['help', 'version'].includes(c)) assert.match(HELP, new RegExp(`^  ${c}\\b`, 'm'), `l2m --help lists ${c}`);
    }
  });

  test('generate steps keep their names', () => {
    const steps = [...Object.keys(STEPS), 'all'];
    const gone = Object.entries(CONTRACT.steps).filter(([s, st]) => st === 'stable' && !steps.includes(s)).map(([s]) => s);
    assert.deepEqual(gone, [], `stable generate steps removed or renamed. ${HOW}`);
    assert.deepEqual(steps.filter((s) => !CONTRACT.steps[s]), [], 'classify new steps in test/cli-contract.json and docs/cli.md');
  });

  test('config keys keep their names, and the schema and defaults agree with the contract', () => {
    const keys = Object.keys(SCHEMA.properties);
    const gone = Object.entries(CONTRACT.config).filter(([k, s]) => s === 'stable' && !keys.includes(k)).map(([k]) => k);
    assert.deepEqual(gone, [], `stable l2m.config.json keys removed or renamed. ${HOW}`);
    assert.deepEqual(keys.filter((k) => !CONTRACT.config[k]), [], 'classify new config keys in test/cli-contract.json and docs/cli.md');
    assert.deepEqual(Object.keys(defaultConfig()).filter((k) => !keys.includes(k)), [], 'every key l2m init writes is in the schema');
  });

  test('l2m --help matches the snapshot', () => {
    const r = l2m(W, ['--help']);
    assert.equal(r.status, 0);
    // The version is left out, so a release does not change the snapshot.
    snapshot('help.txt', r.stdout.replaceAll(VERSION, '<version>'));
  });

  test('l2m.config.schema.json matches the snapshot', () => {
    snapshot('l2m.config.schema.json', readFileSync(join(ROOT, 'l2m.config.schema.json'), 'utf8'));
  });

  test('exit codes: 0 success, 2 usage errors, 1 failed checks, 127 no Python', () => {
    assert.equal(l2m(W, ['--version']).status, 0);
    assert.equal(l2m(W, ['help']).status, 0);
    assert.equal(l2m(W, ['bogus']).status, 2, 'unknown command');
    assert.equal(l2m(W, ['init', '--bogus']).status, 2, 'unknown flag');
    assert.equal(l2m(W, ['generate']).status, 2, 'missing step');
    const broken = mkdtempSync(join(W, 'broken-'));
    writeFileSync(join(broken, 'l2m.config.json'), '{"source": ["missing"]}');
    assert.equal(l2m(broken, ['doctor']).status, 1, 'doctor with a missing kit and source');
    const noPython = { ...process.env, PATH: join(W, 'empty-path') };
    delete noPython.L2M_PYTHON;
    assert.equal(l2m(W, ['analyze', 'scan'], noPython).status, 127, 'analyze without Python');
  });

  test('--version and doctor exit 0 with no npm dependencies', () => {
    const pkg = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8'));
    assert.equal(pkg.dependencies, undefined);
    assert.equal(pkg.devDependencies, undefined);
    assert.equal(l2m(W, ['--version']).stdout.trim(), VERSION);
    const r = l2m(mkdtempSync(join(W, 'empty-')), ['doctor']);
    assert.equal(r.status, 0, r.stdout + r.stderr);
  });

  test('stable script subcommands exist', { skip: !findPython() && 'Python 3.9+ not found' }, () => {
    for (const [cmd, subs] of Object.entries(CONTRACT.scriptCommands)) {
      const r = l2m(W, [cmd, '--help']);
      assert.equal(r.status, 0, `l2m ${cmd} --help: ${r.stderr}`);
      // argparse prints the subcommands as {a,b,c} in the usage line.
      const choices = (/\{([a-z,-]+)\}/.exec(r.stdout)?.[1] || '').split(',');
      const gone = Object.entries(subs).filter(([s, st]) => st === 'stable' && !choices.includes(s)).map(([s]) => s);
      assert.deepEqual(gone, [], `stable l2m ${cmd} subcommands removed or renamed. ${HOW}`);
      assert.deepEqual(choices.filter((s) => !subs[s]), [], `classify new l2m ${cmd} subcommands in test/cli-contract.json and docs/cli.md`);
    }
  });

  test('docs/cli.md lists every command, step, flag and config key with its contract status', () => {
    const doc = readFileSync(join(ROOT, 'docs/cli.md'), 'utf8');
    const rows = new Map();
    let section = '';
    for (const line of doc.split('\n')) {
      const h = /^### (.+)$/.exec(line);
      if (h) section = h[1].trim();
      const row = /^\| `([^` ]+)[^`]*` \| (stable|experimental) \|/.exec(line);
      if (row) rows.set(`${section} ${row[1]}`, row[2]);
    }
    const want = [
      ...Object.entries(CONTRACT.commands).map(([k, s]) => [`Commands ${k}`, s]),
      ...Object.entries(CONTRACT.steps).map(([k, s]) => [`Generate steps ${k}`, s]),
      ...Object.entries(CONTRACT.flags.init).map(([k, v]) => [`init flags ${k}`, v.status]),
      ...Object.entries(CONTRACT.flags.generate).map(([k, v]) => [`generate and prompt flags ${k}`, v.status]),
      ...Object.entries(CONTRACT.config).map(([k, s]) => [`Config keys ${k}`, s]),
      ...Object.entries(CONTRACT.scriptCommands).flatMap(([c, subs]) => Object.entries(subs).map(([k, s]) => [`${c} subcommands ${k}`, s])),
      ...Object.keys(CONTRACT.exitCodes).map((k) => [`Exit codes ${k}`, 'stable']),
    ];
    const problems = want.filter(([key, status]) => rows.get(key) !== status).map(([key, status]) => `${key}: contract says ${status}, docs/cli.md says ${rows.get(key) ?? 'nothing'}`);
    assert.deepEqual(problems, []);
  });
});
