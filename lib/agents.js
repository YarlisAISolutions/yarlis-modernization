// Headless agent runners. Each template is the agent's own non-interactive mode with the narrowest permissions that
// let it edit the documents and run the skill scripts. --yolo swaps in the agent's skip-all-permissions mode and is
// opt-in only. Override any template in l2m.config.json under "agents", or pass --agent-cmd.
//
// Tokens: {prompt} is replaced by the prompt text and {prompt_file} by a file holding it. A template with neither
// gets the prompt on stdin.
import { spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

export const BUILTIN = {
  // Claude Code: `claude -p` reads the prompt from stdin; skills load from .claude/skills.
  claude: {
    cmd: ['claude', '-p', '--permission-mode', 'acceptEdits',
      '--allowedTools', 'Read Write Edit Glob Grep Bash(python3 *) Bash(python *) Bash(git *) Bash(l2m *)'],
    yolo: ['claude', '-p', '--permission-mode', 'bypassPermissions'],
  },
  // OpenAI Codex: `codex exec` reads the prompt from stdin; reads AGENTS.md. workspace-write lets it edit the repo.
  codex: {
    cmd: ['codex', 'exec', '--sandbox', 'workspace-write'],
    yolo: ['codex', 'exec', '--dangerously-bypass-approvals-and-sandbox'],
  },
  // GitHub Copilot CLI: reads .claude/skills, AGENTS.md and .github/copilot-instructions.md.
  copilot: {
    cmd: ['copilot', '-p', '{prompt}', '--allow-tool', 'write', '--allow-tool', 'shell(python3)',
      '--allow-tool', 'shell(python)', '--allow-tool', 'shell(git)'],
    yolo: ['copilot', '-p', '{prompt}', '--allow-all-tools'],
  },
  // Gemini CLI: reads GEMINI.md (installed by `l2m init --agents gemini`).
  gemini: {
    cmd: ['gemini', '--approval-mode', 'auto_edit', '--allowed-tools', 'run_shell_command(python3),run_shell_command(git)', '-p', '{prompt}'],
    yolo: ['gemini', '--yolo', '-p', '{prompt}'],
  },
};

/** Split a command string like a shell would for quotes only (no expansion, no pipes). */
export function splitCommand(s) {
  const out = [];
  for (const m of s.matchAll(/"((?:\\.|[^"\\])*)"|'([^']*)'|(\S+)/g)) out.push(m[1]?.replace(/\\(.)/g, '$1') ?? m[2] ?? m[3]);
  return out;
}

/** The command template for an agent: { cmd: [...] } */
export function resolveAgent(name, { cfg = {}, agentCmd, yolo = false } = {}) {
  if (agentCmd) return { name: 'cmd', cmd: splitCommand(agentCmd) };
  if (cfg.agents?.[name]) return { name, cmd: cfg.agents[name][yolo ? 'yolo' : 'cmd'] || cfg.agents[name].cmd };
  const b = BUILTIN[name];
  if (!b) throw new Error(`unknown agent "${name}"; use ${Object.keys(BUILTIN).join(', ')}, or --agent-cmd "<command> {prompt}"`);
  return { name, cmd: yolo ? b.yolo : b.cmd };
}

/** True when the agent's executable runs (`<exe> --version`). */
export function available(cmd) {
  const r = spawnSync(cmd[0], ['--version'], { stdio: 'ignore', shell: process.platform === 'win32' });
  return !r.error && r.status === 0;
}

/** Run the agent in cwd with the prompt; returns its exit code. */
export function runAgent(agent, prompt, { cwd }) {
  const tmp = mkdtempSync(join(tmpdir(), 'l2m-'));
  const file = join(tmp, 'prompt.md');
  writeFileSync(file, prompt);
  try {
    const usesToken = agent.cmd.some((a) => a.includes('{prompt}') || a.includes('{prompt_file}'));
    // Windows needs a shell to find .cmd shims, and cmd.exe would interpret the prompt text.
    if (process.platform === 'win32' && agent.cmd.some((a) => a.includes('{prompt}'))) {
      throw new Error(`on Windows, pass the prompt on stdin or as {prompt_file}: set agents.${agent.name}.cmd in l2m.config.json`);
    }
    const argv = agent.cmd.map((a) => a.replaceAll('{prompt_file}', file).replaceAll('{prompt}', prompt));
    const r = spawnSync(argv[0], argv.slice(1), {
      cwd, input: usesToken ? undefined : prompt, stdio: [usesToken ? 'inherit' : 'pipe', 'inherit', 'inherit'],
      shell: process.platform === 'win32',
    });
    if (r.error) throw new Error(`${argv[0]}: ${r.error.message}`);
    return r.status ?? 1;
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}
