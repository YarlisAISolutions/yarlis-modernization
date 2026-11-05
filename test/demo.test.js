// Checks of the CardDemo walkthrough in docs/demo (MOD-2). These need no CardDemo checkout:
// scripts/check-demo.sh re-runs the deterministic half against CardDemo in CI. Run: node --test test/
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, relative } from 'node:path';
import { describe, test } from 'node:test';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const DEMO = join(ROOT, 'docs/demo');
const OUT = join(DEMO, 'output');
const FEATURE = join(OUT, 'requirements/user-admin/sign-on');
const DOCVER = join(ROOT, '.claude/skills/requirements-docs/scripts/docver.py');
const INVENTORY = join(ROOT, '.claude/skills/legacy-code-analysis/scripts/inventory.py');
// Every extension the analyzer reads as legacy source or data (EXT_TYPES minus modern languages and plain docs).
const MODERN = ['java', 'kotlin', 'scala', 'groovy', 'csharp', 'vbnet', 'python', 'ruby', 'go', 'javascript', 'typescript',
  'php', 'c', 'cpp', 'rust', 'xml', 'json', 'yaml', 'properties', 'doc', 'text'];
const legacyExtensions = () => {
  const code = 'import importlib.util,json,sys\n'
    + 's=importlib.util.spec_from_file_location("inv",sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n'
    + 'print(json.dumps(sorted(k for k,v in m.EXT_TYPES.items() if v not in json.loads(sys.argv[2]))))';
  const r = spawnSync('python3', ['-c', code, INVENTORY, JSON.stringify(MODERN)], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
  return JSON.parse(r.stdout);
};
const LEGACY_EXT = new RegExp(`\\.(${legacyExtensions().join('|')})$`, 'i');

const read = (p) => readFileSync(p, 'utf8');
const docver = (...args) => spawnSync('python3', [DOCVER, ...args], { encoding: 'utf8' });
const walk = (dir) => readdirSync(dir, { withFileTypes: true })
  .flatMap((e) => (e.isDirectory() ? walk(join(dir, e.name)) : [join(dir, e.name)]));
const shBlocks = (md) => [...md.matchAll(/```sh\n([\s\S]*?)```/g)].map((m) => m[1]);
const pinIn = (text) => text.match(/\b[0-9a-f]{40}\b/)?.[0];

describe('CardDemo demo (docs/demo)', () => {
  test('the README Results section links to the walkthrough', () => {
    const readme = read(join(ROOT, 'README.md'));
    const results = readme.split(/^## Results$/m)[1]?.split(/^## /m)[0] ?? '';
    assert.match(results, /\]\(docs\/demo\/README\.md\)/, 'README "## Results" must link to docs/demo/README.md');
  });

  test('the output holds BRD, FRD, SRD, RTM and gap report, each with a version header', () => {
    for (const [file, type] of [['BRD.md', 'BRD'], ['FRD.md', 'FRD'], ['SRD.md', 'SRD'], ['RTM.md', 'RTM'], ['GAP-REPORT.md', 'GAP']]) {
      const p = join(FEATURE, file);
      assert.ok(existsSync(p), `${relative(ROOT, p)} is missing`);
      const fm = read(p).split(/^---$/m)[1] ?? '';
      assert.match(fm, new RegExp(`^doc_type: ${type}$`, 'm'), `${file}: doc_type`);
      assert.match(fm, /^version: \d+\.\d+\.\d+$/m, `${file}: version header`);
    }
    assert.match(read(join(OUT, 'requirements/PROJECT-CONTEXT.md')), /^version: \d+\.\d+\.\d+$/m);
  });

  test('the output holds the legacy → target mapping for the slice, versioned in the SRD', () => {
    for (const f of ['analysis/slice.json', 'analysis/target-mapping.md', 'analysis/data-mapping.md']) {
      assert.ok(existsSync(join(OUT, f)), `docs/demo/output/${f} is missing`);
    }
    const slice = JSON.parse(read(join(OUT, 'analysis/slice.json')));
    assert.deepEqual(slice.transactions, ['CC00', 'CU01']);
    const mapping = read(join(OUT, 'analysis/target-mapping.md'));
    for (const p of slice.programs) assert.match(mapping, new RegExp(`\\| ${p} \\|`), `mapping row for ${p}`);
    const srd = read(join(FEATURE, 'SRD.md'));
    for (const p of slice.programs) assert.match(srd, new RegExp(p), `SRD cites ${p} in its component mapping`);
  });

  test('the committed documents pass docver.py validate and check', () => {
    const v = docver('validate', FEATURE);
    assert.equal(v.status, 0, v.stdout + v.stderr);
    const c = docver('check', join(OUT, 'requirements'));
    assert.equal(c.status, 0, c.stdout + c.stderr);
  });

  test('structural drift fails validate: a missing required section is an error', () => {
    const w = mkdtempSync(join(process.env.L2M_TEST_TMP || tmpdir(), 'l2m-demo-'));
    try {
      cpSync(join(OUT, 'requirements'), w, { recursive: true });
      const brd = join(w, 'user-admin/sign-on/BRD.md');
      const text = read(brd);
      const broken = text.replace(/^## 11\. .*$/m, '## Eleven');
      assert.notEqual(broken, text, 'BRD has a section 11 heading to remove');
      writeFileSync(brd, broken);
      const v = docver('validate', join(w, 'user-admin/sign-on'));
      assert.notEqual(v.status, 0, 'validate must fail on a drifted structure');
    } finally {
      rmSync(w, { recursive: true, force: true });
    }
  });

  test('the no-source guard covers every legacy extension the analyzer reads', () => {
    for (const f of ['A.cbl', 'B.cob', 'C.cobol', 'D.copy', 'E.cpb', 'F.job', 'G.pli', 'H.pl1', 'I.rexx', 'J.rpg', 'K.CPY', 'L.ezt']) {
      assert.match(f, LEGACY_EXT, f);
    }
    for (const f of ['README.md', 'slice.json', 'check-demo.sh', 'demo.test.js']) assert.doesNotMatch(f, LEGACY_EXT, f);
  });

  test('no legacy source is committed: none under docs/demo, none outside the synthetic fixture', () => {
    const inDemo = walk(DEMO).filter((p) => LEGACY_EXT.test(p)).map((p) => relative(ROOT, p));
    assert.deepEqual(inDemo, []);
    const ls = spawnSync('git', ['ls-files'], { cwd: ROOT, encoding: 'utf8' });
    if (ls.status !== 0) return; // not a git checkout (e.g. an unpacked tarball): the docs/demo check above still ran
    const tracked = ls.stdout.split('\n').filter((p) => LEGACY_EXT.test(p) && !p.startsWith('tests/fixtures/mini/'));
    assert.deepEqual(tracked, []);
  });

  test('the walkthrough pins CardDemo to the same commit as scripts/check-demo.sh and uses only real commands', () => {
    const md = read(join(DEMO, 'README.md'));
    const script = read(join(ROOT, 'scripts/check-demo.sh'));
    const pin = pinIn(script.match(/^CARDDEMO_SHA=.*$/m)?.[0] ?? '');
    assert.ok(pin, 'scripts/check-demo.sh sets CARDDEMO_SHA');
    assert.ok(md.includes(pin), `docs/demo/README.md pins CardDemo at ${pin}`);
    assert.match(read(join(OUT, 'requirements/PROJECT-CONTEXT.md')), new RegExp(`^repo_ref: "?${pin}"?$`, 'm'));
    const contract = JSON.parse(read(join(ROOT, 'test/cli-contract.json')));
    const used = shBlocks(md).flatMap((b) => [...b.matchAll(/(?:^|[\s;&|(])l2m (\w[\w-]*)/g)].map((m) => m[1]));
    assert.ok(used.length >= 6, 'the walkthrough runs l2m commands');
    for (const cmd of used) assert.ok(cmd in contract.commands, `l2m ${cmd} is a command in test/cli-contract.json`);
    assert.ok(shBlocks(md).some((b) => b.includes('log -1 --format=%H -- docs/demo/output')),
      'the walkthrough checks out the yarlis-modernization commit that recorded docs/demo/output');
    for (const step of ['init', 'analyze scan', 'analyze slice', 'map', 'generate', 'docs rtm sync', 'docs validate']) {
      assert.ok(shBlocks(md).some((b) => b.includes(`l2m ${step}`)), `the walkthrough runs l2m ${step}`);
    }
  });
});
