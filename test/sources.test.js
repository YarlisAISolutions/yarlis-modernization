// Several source trees in l2m.config.json: every tree is scanned into its own analysis folder. Run: node --test test/
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { after, before, describe, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { analysisDirs } from '../lib/generate.js';
import { validateConfig } from '../lib/config.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const BIN = join(ROOT, 'bin/l2m.js');
const l2m = (cwd, ...args) => spawnSync(process.execPath, [BIN, ...args], { cwd, encoding: 'utf8', env: { ...process.env, NO_COLOR: '1' } });
const git = (cwd, ...args) => spawnSync('git', ['-c', 'user.email=t@t', '-c', 'user.name=t', ...args], { cwd, encoding: 'utf8' });

let W;
before(() => {
  W = mkdtempSync(join(process.env.L2M_TEST_TMP || tmpdir(), 'l2m-sources-'));
  for (const tree of ['legacy/online', 'legacy/batch']) cpSync(join(ROOT, 'tests/fixtures/mini'), join(W, tree), { recursive: true });
  git(W, 'init', '-q', '-b', 'main');
  assert.equal(l2m(W, 'init', '--agents', 'claude', '--project', 'Two').status, 0);
  const cfg = JSON.parse(readFileSync(join(W, 'l2m.config.json'), 'utf8'));
  writeFileSync(join(W, 'l2m.config.json'), `${JSON.stringify({ ...cfg, source: ['legacy/online', 'legacy/batch'] }, null, 2)}\n`);
  git(W, 'add', '-A');
  git(W, 'commit', '-qm', 'two trees');
});
after(() => rmSync(W, { recursive: true, force: true }));

describe('several source trees', () => {
  test('generate analysis scans every tree into its own folder and names them all in the prompt', () => {
    const r = l2m(W, 'prompt', 'analysis', '--scope', 'AU01');
    assert.equal(r.status, 0, r.stderr);
    for (const d of ['legacy-online', 'legacy-batch']) {
      const inv = JSON.parse(readFileSync(join(W, 'docs/analysis', d, 'inventory.json'), 'utf8'));
      assert.equal(inv.summary.programs, 3, `${d} scanned`);
    }
    assert.ok(!existsSync(join(W, 'docs/analysis/inventory.json')), 'no top-level inventory with several trees');
    assert.match(r.stderr, /Scanning legacy\/online → docs\/analysis\/legacy-online\//);
    assert.match(r.stderr, /Scanning legacy\/batch → docs\/analysis\/legacy-batch\//);
    assert.match(r.stdout, /one folder per source tree: legacy\/online → docs\/analysis\/legacy-online\/, legacy\/batch → docs\/analysis\/legacy-batch\//);
  });

  test('srd drafts the target mapping for every tree', () => {
    const r = l2m(W, 'prompt', 'srd', '--module', 'accounts', '--feature', 'account-update', '--scope', 'AU01');
    assert.equal(r.status, 0, r.stderr);
    for (const d of ['legacy-online', 'legacy-batch']) assert.ok(existsSync(join(W, 'docs/analysis', d, 'target-mapping.md')), `${d} mapped`);
    assert.match(r.stdout, /docs\/analysis\/legacy-online\/target-mapping\.md, docs\/analysis\/legacy-batch\/target-mapping\.md/);
  });

  test('--schema-diff writes a report per tree', () => {
    const ddl = join(W, 'legacy/batch/ddl/ACCOUNT.ddl');
    writeFileSync(ddl, readFileSync(ddl, 'utf8').replace('CURR_BAL     DECIMAL(12,2) NOT NULL,', 'CURR_BAL     DECIMAL(13,2) NOT NULL,'));
    const r = l2m(W, 'prompt', 'change-request', '--module', 'accounts', '--feature', 'account-update', '--cr', 'CR-001',
      '--summary', 'Widen the balance', '--schema-diff', 'HEAD');
    assert.equal(r.status, 0, r.stderr);
    assert.match(readFileSync(join(W, 'docs/analysis/legacy-batch/schema-diff-HEAD-worktree.md'), 'utf8'), /column changed: CURR_BAL/);
    assert.doesNotMatch(readFileSync(join(W, 'docs/analysis/legacy-online/schema-diff-HEAD-worktree.md'), 'utf8'), /column changed/);
    assert.match(r.stdout, /docs\/analysis\/legacy-online\/schema-diff-HEAD-worktree\.md, docs\/analysis\/legacy-batch\/schema-diff-HEAD-worktree\.md/);
  });

  test('a single tree still goes to the analysis folder itself', () => {
    const r = l2m(W, 'prompt', 'analysis', '--scope', 'AU01', '--src', 'legacy/online');
    assert.equal(r.status, 0, r.stderr);
    assert.ok(existsSync(join(W, 'docs/analysis/inventory.json')));
    assert.doesNotMatch(r.stdout, /one folder per source tree/);
  });
});

describe('analysisDirs', () => {
  test('one folder per tree, named after the entry, never colliding', () => {
    assert.deepEqual(analysisDirs(validateConfig({ source: ['app'] })), [{ source: 'app', dir: 'docs/analysis' }]);
    assert.deepEqual(analysisDirs(validateConfig({ source: [] })), []);
    assert.deepEqual(analysisDirs(validateConfig({ source: ['../cobol/app', 'jcl/app', 'APP', 'app'] })).map((t) => t.dir),
      ['docs/analysis/cobol-app', 'docs/analysis/jcl-app', 'docs/analysis/app', 'docs/analysis/app-2']);
  });
});
