// The Copilot and Gemini command lines l2m builds, checked against each CLI's documented options (see lib/agents.js)
// and end to end through stand-in executables on PATH. Run: node --test test/
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { delimiter, dirname, join } from 'node:path';
import { after, before, describe, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { BUILTIN, resolveAgent } from '../lib/agents.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const BIN = join(ROOT, 'bin/l2m.js');

// `copilot --allow-tool` patterns: Kind(argument); a shell rule matches a command with any arguments only with `:*`.
const COPILOT_TOOL = /^(write|read|shell\([a-z0-9_.-]+:\*\))$/;
// `gemini --allowed-tools`: comma-separated tool names, run_shell_command(<command prefix>).
const GEMINI_TOOL = /^run_shell_command\([a-z0-9_.-]+\)$/;
const values = (argv, flag) => argv.flatMap((a, i) => (argv[i - 1] === flag ? [a] : []));

describe('agent templates', () => {
  test('copilot: -p {prompt} and documented --allow-tool patterns', () => {
    const { cmd } = resolveAgent('copilot');
    assert.deepEqual(cmd.slice(0, 3), ['copilot', '-p', '{prompt}']);
    const tools = values(cmd, '--allow-tool');
    assert.deepEqual(tools, ['write', 'shell(python3:*)', 'shell(python:*)', 'shell(git:*)']);
    for (const t of tools) assert.match(t, COPILOT_TOOL);
    assert.deepEqual(resolveAgent('copilot', { yolo: true }).cmd, ['copilot', '-p', '{prompt}', '--allow-all-tools']);
  });

  test('gemini: -p {prompt}, a valid approval mode, documented tool names, folder trusted for the run', () => {
    const a = resolveAgent('gemini');
    assert.deepEqual(a.cmd.slice(-2), ['-p', '{prompt}']);
    assert.ok(['default', 'auto_edit', 'yolo', 'plan'].includes(values(a.cmd, '--approval-mode')[0]));
    const tools = values(a.cmd, '--allowed-tools')[0].split(',');
    assert.deepEqual(tools, ['run_shell_command(python3)', 'run_shell_command(git)']);
    for (const t of tools) assert.match(t, GEMINI_TOOL);
    assert.deepEqual(a.env, { GEMINI_CLI_TRUST_WORKSPACE: 'true' });
    const y = resolveAgent('gemini', { yolo: true });
    assert.deepEqual(y.cmd, ['gemini', '--yolo', '-p', '{prompt}']);
    assert.deepEqual(y.env, a.env);
  });

  test('no template is marked unverified', () => {
    assert.doesNotMatch(readFileSync(join(ROOT, 'lib/agents.js'), 'utf8'), /Unverified/);
    assert.deepEqual(Object.keys(BUILTIN), ['claude', 'codex', 'copilot', 'gemini']);
  });
});

describe('generate --agent copilot|gemini', { skip: process.platform === 'win32' && 'stand-in agents are sh scripts' }, () => {
  let W;
  let FAKE;
  before(() => {
    W = mkdtempSync(join(process.env.L2M_TEST_TMP || tmpdir(), 'l2m-agents-'));
    FAKE = join(W, '.bin');
    mkdirSync(FAKE);
    // Stand-in CLIs: answer --version, record argv (NUL-separated) and the trust variable.
    for (const name of ['copilot', 'gemini']) {
      writeFileSync(join(FAKE, name), `#!/bin/sh
[ "$1" = --version ] && exit 0
printf '%s\\0' "$@" > "$PWD/${name}.argv"
printf '%s' "\${GEMINI_CLI_TRUST_WORKSPACE-unset}" > "$PWD/${name}.trust"
`);
      chmodSync(join(FAKE, name), 0o755);
    }
    const r = spawnSync(process.execPath, [BIN, 'init', '--agents', 'copilot,gemini', '--project', 'Agents'], { cwd: W, encoding: 'utf8' });
    assert.equal(r.status, 0, r.stderr);
  });
  after(() => rmSync(W, { recursive: true, force: true }));

  const run = (agent, env = {}) => {
    const { GEMINI_CLI_TRUST_WORKSPACE, ...base } = process.env;
    const r = spawnSync(process.execPath, [BIN, 'generate', 'analysis', '--scope', 'AU01', '--agent', agent],
      { cwd: W, encoding: 'utf8', env: { ...base, PATH: `${FAKE}${delimiter}${process.env.PATH}`, ...env } });
    assert.equal(r.status, 0, r.stderr);
    assert.match(r.stderr, new RegExp(`running ${agent}`));
    return { argv: readFileSync(join(W, `${agent}.argv`), 'utf8').split('\0').slice(0, -1), trust: readFileSync(join(W, `${agent}.trust`), 'utf8') };
  };

  test('copilot gets the prompt as the -p value and the allow-tool rules', () => {
    const { argv, trust } = run('copilot');
    assert.equal(argv[0], '-p');
    assert.match(argv[1], /^Use the Agent Skills in \.claude\/skills/);
    assert.match(argv[1], /## 3\. Task\nAnalyze the existing code for AU01/);
    assert.deepEqual(argv.slice(2), ['--allow-tool', 'write', '--allow-tool', 'shell(python3:*)', '--allow-tool', 'shell(python:*)', '--allow-tool', 'shell(git:*)']);
    assert.equal(trust, 'unset', 'copilot gets no extra environment');
  });

  test('gemini gets the approval mode, the allowed tools, the prompt and a trusted folder', () => {
    const { argv, trust } = run('gemini');
    assert.deepEqual(argv.slice(0, 5), ['--approval-mode', 'auto_edit', '--allowed-tools', 'run_shell_command(python3),run_shell_command(git)', '-p']);
    assert.match(argv[5], /## 3\. Task\nAnalyze the existing code for AU01/);
    assert.equal(argv.length, 6);
    assert.equal(trust, 'true');
  });

  test("the user's own GEMINI_CLI_TRUST_WORKSPACE wins", () => {
    assert.equal(run('gemini', { GEMINI_CLI_TRUST_WORKSPACE: 'false' }).trust, 'false');
  });
});
