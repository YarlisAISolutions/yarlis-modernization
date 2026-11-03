// Change requests: l2m fixes each document's next version, so the same request on the same documents always gives the
// same numbers, and it fails the run when the agent bumps to anything else. Run: node --test test/
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { after, before, describe, test } from 'node:test';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const BIN = join(ROOT, 'bin/l2m.js');
const F = 'docs/requirements/accounts/account-update';
const CR = ['--module', 'accounts', '--feature', 'account-update', '--cr', 'CR-009', '--summary', 'Audit credit limit changes'];
const l2m = (cwd, args, env = {}) => spawnSync(process.execPath, [BIN, ...args], { cwd, encoding: 'utf8', env: { ...process.env, NO_COLOR: '1', ...env } });
const fixed = (prompt) => prompt.match(/^- New versions, fixed by l2m.*$/m)?.[0];
const version = (W, doc) => readFileSync(join(W, F, doc), 'utf8').match(/^version:\s*(\S+)/m)[1];

// Stand-in agent: bumps the documents l2m lists with docver.py, either to the given versions or (BUMP=major) wrongly.
const AGENT = `
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
const prompt = readFileSync(0, 'utf8');
const line = prompt.match(/New versions, fixed by l2m[^:]*: (.*)/)[1];
for (const [, path] of line.matchAll(/(\\S+\\.md) \\S+ → \\S+/g)) {
  spawnSync('python3', ['.claude/skills/requirements-docs/scripts/docver.py', 'bump', path, '--level', process.env.BUMP || 'minor',
    '--summary', 'CR-009: audit', '--sections', '10'], { stdio: 'inherit' });
}
`;

let W;
before(() => {
  W = mkdtempSync(join(process.env.L2M_TEST_TMP || tmpdir(), 'l2m-cr-'));
  cpSync(join(ROOT, 'tests/fixtures/mini'), join(W, 'legacy'), { recursive: true });
  spawnSync('git', ['init', '-q', '-b', 'main'], { cwd: W });
  assert.equal(l2m(W, ['init', '--agents', 'claude', '--src', 'legacy', '--project', 'Mini']).status, 0);
  writeFileSync(join(W, 'bump-agent.mjs'), AGENT);
});
after(() => rmSync(W, { recursive: true, force: true }));

describe('change-request versions', () => {
  test('the same request on the same documents gives the same versions, and the prompt writes nothing', () => {
    const a = l2m(W, ['prompt', 'change-request', ...CR]);
    assert.equal(a.status, 0, a.stderr);
    const b = l2m(W, ['prompt', 'change-request', ...CR]);
    assert.equal(fixed(a.stdout), fixed(b.stdout));
    assert.equal(fixed(a.stdout), `- New versions, fixed by l2m (bump each document to exactly this version; l2m checks them afterwards): ${F}/BRD.md 0.1.0 → 0.2.0, ${F}/FRD.md 0.1.0 → 0.2.0, ${F}/SRD.md 0.1.0 → 0.2.0`);
    assert.equal(version(W, 'BRD.md'), '0.1.0');
    assert.ok(!existsSync(join(W, F, 'history')), 'the dry run snapshots nothing');
  });

  test('--affects limits the documents', () => {
    const r = l2m(W, ['prompt', 'change-request', ...CR, '--affects', 'FRD']);
    assert.match(fixed(r.stdout), new RegExp(`: ${F}/FRD\\.md 0\\.1\\.0 → 0\\.2\\.0$`));
  });

  test('generate fails when the agent bumps to another version', () => {
    const r = l2m(W, ['generate', 'change-request', ...CR, '--agent-cmd', `"${process.execPath}" bump-agent.mjs`], { BUMP: 'major' });
    // Put the documents back for the next test.
    for (const d of ['BRD', 'FRD', 'SRD']) cpSync(join(W, F, 'history', `${d}_v0.1.0.md`), join(W, F, `${d}.md`));
    rmSync(join(W, F, 'history'), { recursive: true });
    assert.notEqual(r.status, 0, r.stdout + r.stderr);
    assert.match(r.stderr, new RegExp(`${F}/BRD\\.md is at 1\\.0\\.0, expected 0\\.2\\.0`));
  });

  test('generate accepts the fixed versions', () => {
    // The scaffolded documents are still empty, so validate fails; the version check itself must not.
    const r = l2m(W, ['generate', 'change-request', ...CR, '--agent-cmd', `"${process.execPath}" bump-agent.mjs`]);
    assert.doesNotMatch(r.stderr, /expected 0\.2\.0/);
    for (const d of ['BRD.md', 'FRD.md', 'SRD.md']) assert.equal(version(W, d), '0.2.0');
  });
});
