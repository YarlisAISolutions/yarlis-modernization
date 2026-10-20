// End-to-end tests of the l2m CLI against tests/fixtures/mini. Run: node --test test/
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { after, before, describe, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { splitCommand } from '../lib/agents.js';
import { validateConfig } from '../lib/config.js';
import { plan } from '../lib/install.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const BIN = join(ROOT, 'bin/l2m.js');
const FAKE = join(ROOT, 'test/fake-agent.js');
const PLACEHOLDER = /\[[A-Z][A-Z0-9 _/.,|-]*[A-Z0-9]\](?!\()/;

const l2m = (cwd, ...args) => spawnSync(process.execPath, [BIN, ...args], { cwd, encoding: 'utf8', env: { ...process.env, NO_COLOR: '1' } });
const git = (cwd, ...args) => spawnSync('git', ['-c', 'user.email=t@t', '-c', 'user.name=t', ...args], { cwd, encoding: 'utf8' });

let W;
before(() => {
  W = mkdtempSync(join(process.env.L2M_TEST_TMP || tmpdir(), 'l2m-test-'));
  cpSync(join(ROOT, 'tests/fixtures/mini'), join(W, 'legacy'), { recursive: true });
  git(W, 'init', '-q', '-b', 'main');
  git(W, 'add', '-A');
  git(W, 'commit', '-qm', 'legacy');
});
after(() => rmSync(W, { recursive: true, force: true }));

describe('l2m', () => {
  test('--version matches package.json', () => {
    const r = l2m(W, '--version');
    assert.equal(r.status, 0);
    assert.equal(r.stdout.trim(), JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8')).version);
  });

  test('plugin marketplace version matches package.json', () => {
    const pkg = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8'));
    const market = JSON.parse(readFileSync(join(ROOT, '.claude-plugin/marketplace.json'), 'utf8'));
    assert.equal(market.plugins[0].version, pkg.version);
  });

  test('unknown command exits 2', () => {
    assert.equal(l2m(W, 'bogus').status, 2);
  });

  test('init installs the kit, config and project context; a second run keeps everything', () => {
    const r = l2m(W, 'init', '--src', 'legacy', '--project', 'Mini');
    assert.equal(r.status, 0, r.stderr);
    for (const p of ['.claude/skills/requirements-docs/SKILL.md', '.claude/skills/legacy-code-analysis/scripts/inventory.py',
      '.github/copilot-instructions.md', '.github/workflows/requirements-check.yml', 'AGENTS.md', 'GEMINI.md',
      'prompts/02-generate-brd.md', 'l2m.config.json', 'docs/requirements/PROJECT-CONTEXT.md', 'docs/inputs', '.claude/skills/.l2m-version']) {
      assert.ok(existsSync(join(W, p)), `${p} installed`);
    }
    assert.ok(!existsSync(join(W, '.claude/skills/requirements-docs/scripts/__pycache__')), 'no __pycache__ copied');
    assert.deepEqual(JSON.parse(readFileSync(join(W, 'l2m.config.json'), 'utf8')).source, ['legacy']);
    const again = l2m(W, 'init');
    assert.equal(again.status, 0);
    assert.doesNotMatch(again.stdout, /^(add|append|update) /m, 'nothing added or replaced on a second run');
  });

  test('init --agents claude installs only what Claude Code needs', () => {
    const d = mkdtempSync(join(W, 'claude-only-'));
    assert.equal(l2m(d, 'init', '--agents', 'claude').status, 0);
    assert.ok(existsSync(join(d, '.claude/skills/requirements-docs/SKILL.md')));
    assert.ok(!existsSync(join(d, '.github/copilot-instructions.md')));
    assert.ok(!existsSync(join(d, 'AGENTS.md')));
  });

  test('analyze passes arguments and the exit code through', () => {
    const r = l2m(W, 'analyze', 'scan', '--src', 'legacy', '--out', 'docs/analysis');
    assert.equal(r.status, 0, r.stderr);
    assert.equal(JSON.parse(readFileSync(join(W, 'docs/analysis/inventory.json'), 'utf8')).summary.unresolved, 0);
    assert.notEqual(l2m(W, 'docs', 'validate', 'does-not-exist').status, 0);
  });

  test('prompt brd: scaffolds the feature, writes the inputs manifest, leaves no placeholders', () => {
    writeFileSync(join(W, 'docs/inputs/interview.md'), 'Account maintenance interview notes\n');
    const r = l2m(W, 'prompt', 'brd', '--module', 'accounts', '--feature', 'account-update', '--scope', 'AU01 (ACCTUPD)');
    assert.equal(r.status, 0, r.stderr);
    assert.ok(existsSync(join(W, 'docs/requirements/accounts/account-update/BRD.md')));
    assert.doesNotMatch(r.stdout, PLACEHOLDER);
    assert.match(r.stdout, /## 3\. Task\nWrite the Business Requirements Document for Account update/);
    assert.match(r.stdout, /docs\/analysis\/inputs\.md/);
    assert.match(readFileSync(join(W, 'docs/analysis/inputs.md'), 'utf8'), /\[docs\/inputs\/interview\.md\]\(\.\.\/inputs\/interview\.md\) \| markdown/);
    assert.doesNotMatch(r.stdout, /Scanning|Scaffolded/, 'status goes to stderr, not into the prompt');
  });

  test('every step builds a prompt with no placeholders', () => {
    for (const step of ['analysis', 'frd', 'srd', 'assess']) {
      const r = l2m(W, 'prompt', step, '--module', 'accounts', '--feature', 'account-update', '--scope', 'AU01');
      assert.equal(r.status, 0, `${step}: ${r.stderr}`);
      assert.doesNotMatch(r.stdout, PLACEHOLDER, step);
      for (let n = 1; n <= 8; n++) assert.match(r.stdout, new RegExp(`^## ${n}\\. `, 'm'), `${step} §${n}`);
    }
  });

  test('missing flags are usage errors', () => {
    assert.equal(l2m(W, 'prompt', 'brd', '--module', 'accounts', '--feature', 'account-update').status, 2);
    assert.equal(l2m(W, 'prompt', 'brd', '--module', 'Accounts', '--feature', 'x', '--scope', 'y').status, 2);
    assert.equal(l2m(W, 'prompt', 'change-request', '--module', 'accounts', '--feature', 'account-update').status, 2);
    assert.equal(l2m(W, 'prompt', 'nope').status, 2);
  });

  test('generate runs the agent (stdin) and post-checks with validate', () => {
    const r = l2m(W, 'generate', 'brd', '--module', 'accounts', '--feature', 'account-update', '--scope', 'AU01',
      '--agent-cmd', `"${process.execPath}" "${FAKE}"`);
    const validate = l2m(W, 'docs', 'validate', 'docs/requirements/accounts/account-update/BRD.md');
    assert.equal(r.status, validate.status, r.stdout + r.stderr);
    assert.match(readFileSync(join(W, 'agent-prompt.md'), 'utf8'), /## 7\. Rules/);
    const brd = readFileSync(join(W, 'docs/requirements/accounts/account-update/BRD.md'), 'utf8');
    assert.match(brd, /### BR-001/);
    assert.match(brd, /\[`cbl\/ACCTUPD\.cbl:24-31`\]\([^)]*ACCTUPD\.cbl#L24-L31\)/, 'post-check linkified the evidence');
    assert.ok(existsSync(join(W, 'docs/requirements/INDEX.md')), 'post-check wrote the index');
  });

  test('generate passes {prompt_file} and returns the agent exit code', () => {
    const r = spawnSync(process.execPath, [BIN, 'generate', 'brd', '--module', 'accounts', '--feature', 'account-update',
      '--scope', 'AU01', '--agent-cmd', `"${process.execPath}" "${FAKE}" {prompt_file}`], { cwd: W, encoding: 'utf8', env: { ...process.env, FAKE_AGENT_EXIT: '3' } });
    assert.equal(r.status, 3, r.stderr);
  });

  test('change-request with --schema-diff links a report of tables, programs and requirements', () => {
    git(W, 'add', '-A');
    git(W, 'commit', '-qm', 'kit and docs');
    const ddl = join(W, 'legacy/ddl/ACCOUNT.ddl');
    writeFileSync(ddl, readFileSync(ddl, 'utf8').replace('CURR_BAL     DECIMAL(12,2) NOT NULL,', 'CURR_BAL     DECIMAL(13,2) NOT NULL,\n    LAST_TXN_TS  TIMESTAMP,'));
    const r = l2m(W, 'prompt', 'change-request', '--module', 'accounts', '--feature', 'account-update', '--cr', 'CR-007',
      '--summary', 'Track the last transaction time', '--schema-diff', 'HEAD', '--author', 'Test');
    assert.equal(r.status, 0, r.stderr);
    assert.doesNotMatch(r.stdout, PLACEHOLDER);
    assert.match(r.stdout, /Change request CR-007: Track the last transaction time\./);
    assert.match(r.stdout, /--summary "CR-007: \.\.\." --sections "\.\.\." --author "Test"/);
    const report = readFileSync(join(W, 'docs/analysis/schema-diff-HEAD-worktree.md'), 'utf8');
    assert.match(report, /column changed: CURR_BAL DECIMAL\(12,2\) NOT NULL → DECIMAL\(13,2\) NOT NULL/);
    assert.match(report, /column added: LAST_TXN_TS TIMESTAMP/);
    assert.match(report, /\| ACCTPOST \|/);
    // BR-001 cites ACCTUPD, which reads ACCOUNT through a CICS file, not DB2: correctly not affected.
    assert.doesNotMatch(report, /BR-001/);
  });

  test('doctor reports the repository as ready', () => {
    const r = l2m(W, 'doctor');
    assert.match(r.stdout, /ok {3}skill requirements-docs/);
    assert.match(r.stdout, /ok {3}kit version/);
  });
});

describe('units', () => {
  test('splitCommand handles quotes', () => {
    assert.deepEqual(splitCommand(`my-agent --x "a b" 'c d' {prompt}`), ['my-agent', '--x', 'a b', 'c d', '{prompt}']);
  });
  test('config validation', () => {
    assert.deepEqual(validateConfig({ source: 'src' }).source, ['src']);
    assert.throws(() => validateConfig({ docs: [1] }), /"docs"/);
    assert.throws(() => validateConfig({ agents: { x: { cmd: [] } } }), /agents\.x\.cmd/);
  });
  test('install plan per agent', () => {
    assert.ok(!plan(['claude']).some((i) => i.rel.startsWith('.github/copilot')));
    assert.ok(plan(['gemini']).some((i) => i.dst === 'GEMINI.md'));
  });
});
