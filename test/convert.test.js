// Word and PDF inputs are converted to Markdown before the inputs manifest is written (MOD-9). Run: node --test test/
// The PDF cases never depend on the host: a fake pdftotext on PATH for "installed", an empty PATH for "missing".
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { delimiter, dirname, join } from 'node:path';
import { after, before, describe, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { findPython } from '../lib/python.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const BIN = join(ROOT, 'bin/l2m.js');
const py = findPython();
const skip = (!py && 'Python 3.9+ not found') || (process.platform === 'win32' && 'the fake pdftotext is a shell script');
const python = py && spawnSync(py.cmd[0], [...py.cmd.slice(1), '-c', 'import sys; print(sys.executable)'], { encoding: 'utf8' }).stdout.trim();
const l2m = (cwd, args, env = process.env) => spawnSync(process.execPath, [BIN, ...args], { cwd, encoding: 'utf8', env: { ...env, NO_COLOR: '1' } });

let W;
const expected = () => spawnSync(python, ['-c', 'import sys; sys.path.insert(0, sys.argv[1]); import make_docx; print(make_docx.EXPECTED, end="")',
  join(ROOT, 'tests')], { encoding: 'utf8' }).stdout;

/** A project with docs/inputs holding spec.docx (synthetic) and scan.pdf. */
function project(name) {
  const dir = join(W, name);
  mkdirSync(dir);
  assert.equal(l2m(dir, ['init', '--agents', 'claude', '--project', 'Convert']).status, 0);
  const r = spawnSync(python, [join(ROOT, 'tests/make_docx.py'), join(dir, 'docs/inputs/spec.docx')], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
  writeFileSync(join(dir, 'docs/inputs/scan.pdf'), '%PDF-1.4 not parsed by the fake tool\n');
  return dir;
}

before(() => { W = mkdtempSync(join(process.env.L2M_TEST_TMP || tmpdir(), 'l2m-convert-')); });
after(() => rmSync(W, { recursive: true, force: true }));

describe('converting Word and PDF inputs', { skip }, () => {
  test('generate writes Markdown next to each input, keeps the prompt clean, and lists the results in the manifest', () => {
    const dir = project('with-tool');
    const bin = join(W, 'fake-bin');
    mkdirSync(bin);
    writeFileSync(join(bin, 'pdftotext'), '#!/bin/sh\nprintf "Account limits\\nare checked daily.\\n\\n# not a heading\\n\\f1. Scope of CURR_BAL\\n"\n');
    chmodSync(join(bin, 'pdftotext'), 0o755);
    writeFileSync(join(dir, 'docs/inputs/notes.docx.md'), 'hand-written notes\n');
    spawnSync(python, [join(ROOT, 'tests/make_docx.py'), join(dir, 'docs/inputs/notes.docx')]);
    const env = { ...process.env, PATH: `${bin}${delimiter}${process.env.PATH}` };

    const r = l2m(dir, ['prompt', 'analysis', '--scope', 'everything'], env);
    assert.equal(r.status, 0, r.stderr);
    const docx = readFileSync(join(dir, 'docs/inputs/spec.docx.md'), 'utf8');
    assert.match(docx, /^<!-- l2m convert v1: generated from spec\.docx \(sha256 [0-9a-f]{12}\)/);
    assert.equal(docx.split('\n').slice(2).join('\n'), expected());
    assert.equal(readFileSync(join(dir, 'docs/inputs/scan.pdf.md'), 'utf8').split('\n').slice(2).join('\n'),
      '<!-- page 1 -->\n\nAccount limits\nare checked daily.\n\n\\# not a heading\n\n<!-- page 2 -->\n\n1\\. Scope of CURR_BAL\n');
    assert.equal(readFileSync(join(dir, 'docs/inputs/notes.docx.md'), 'utf8'), 'hand-written notes\n', 'a file l2m did not write is kept');
    assert.match(r.stderr, /converted docs\/inputs\/spec\.docx -> docs\/inputs\/spec\.docx\.md/);
    assert.match(r.stderr, /Warning: skip docs\/inputs\/notes\.docx: notes\.docx\.md exists and was not written by l2m/);
    assert.doesNotMatch(r.stdout, /converted|Warning/, 'conversion messages stay out of the printed prompt');
    const manifest = readFileSync(join(dir, 'docs/analysis/inputs.md'), 'utf8');
    assert.match(manifest, /\[docs\/inputs\/spec\.docx\.md\]\(\.\.\/inputs\/spec\.docx\.md\) \| markdown/);
    assert.match(manifest, /\[docs\/inputs\/scan\.pdf\.md\]/);

    // A second run with unchanged inputs rewrites nothing.
    const before = statSync(join(dir, 'docs/inputs/spec.docx.md')).mtimeMs;
    const again = l2m(dir, ['prompt', 'analysis', '--scope', 'everything'], env);
    assert.equal(again.status, 0, again.stderr);
    assert.doesNotMatch(again.stderr, /converted/);
    assert.equal(statSync(join(dir, 'docs/inputs/spec.docx.md')).mtimeMs, before);
  });

  test('a single file given with --docs brings its Markdown conversion into the manifest', () => {
    const dir = project('single-file');
    const r = l2m(dir, ['prompt', 'analysis', '--scope', 'everything', '--docs', 'docs/inputs/spec.docx'],
      { ...process.env, PATH: join(W, 'no-such-dir'), L2M_PYTHON: python });
    assert.equal(r.status, 0, r.stderr);
    const manifest = readFileSync(join(dir, 'docs/analysis/inputs.md'), 'utf8');
    assert.match(manifest, /\| document \| \[docs\/inputs\/spec\.docx\]/);
    assert.match(manifest, /\| document \| \[docs\/inputs\/spec\.docx\.md\]/);
  });

  test('without pdftotext the PDF is skipped with the install command and the step still succeeds', () => {
    const dir = project('without-tool');
    const empty = join(W, 'empty-path');
    mkdirSync(empty);
    const r = l2m(dir, ['prompt', 'analysis', '--scope', 'everything'], { ...process.env, PATH: empty, L2M_PYTHON: python });
    assert.equal(r.status, 0, r.stderr);
    assert.match(r.stderr, /Warning: skip docs\/inputs\/scan\.pdf: PDF conversion needs pdftotext from Poppler, which is not on PATH/);
    assert.match(r.stderr, /brew install poppler/);
    assert.ok(existsSync(join(dir, 'docs/inputs/spec.docx.md')), 'the .docx is still converted');
    assert.ok(!existsSync(join(dir, 'docs/inputs/scan.pdf.md')));
  });

  test('l2m docs convert exits 1 when a file is skipped and 0 when everything is converted', () => {
    const dir = project('direct');
    const empty = join(W, 'empty-path-2');
    mkdirSync(empty);
    const env = { ...process.env, PATH: empty, L2M_PYTHON: python };
    const r = l2m(dir, ['docs', 'convert'], env);
    assert.equal(r.status, 1, r.stdout + r.stderr);
    assert.match(r.stdout, /1 converted, 0 up to date, 1 skipped/);
    rmSync(join(dir, 'docs/inputs/scan.pdf'));
    const ok = l2m(dir, ['docs', 'convert'], env);
    assert.equal(ok.status, 0, ok.stdout + ok.stderr);
    assert.match(ok.stdout, /0 converted, 1 up to date, 0 skipped/);
  });
});
