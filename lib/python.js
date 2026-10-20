// Find Python 3.9+ and run the bundled skill scripts. The scripts always run from this package's copy,
// never from a target repository's .claude/skills, so the CLI and its version always match.
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const PKG_ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
export const VERSION = JSON.parse(readFileSync(join(PKG_ROOT, 'package.json'), 'utf8')).version;

export const SCRIPTS = {
  inventory: join(PKG_ROOT, '.claude/skills/legacy-code-analysis/scripts/inventory.py'),
  docver: join(PKG_ROOT, '.claude/skills/requirements-docs/scripts/docver.py'),
  mapgen: join(PKG_ROOT, '.claude/skills/mainframe-modernization/scripts/mapgen.py'),
};

const CANDIDATES = process.platform === 'win32'
  ? [['py', '-3'], ['python'], ['python3']]
  : [['python3'], ['python']];

let found;

/** The Python command as [exe, ...args], or null with the reason in .error. */
export function findPython() {
  if (found !== undefined) return found;
  const tried = [];
  const override = process.env.L2M_PYTHON ? [[process.env.L2M_PYTHON]] : [];
  for (const [exe, ...pre] of [...override, ...CANDIDATES]) {
    const r = spawnSync(exe, [...pre, '-c', 'import sys; print("%d.%d" % sys.version_info[:2])'], { encoding: 'utf8' });
    if (r.status !== 0) continue;
    const [major, minor] = r.stdout.trim().split('.').map(Number);
    tried.push(`${exe} ${major}.${minor}`);
    if (major === 3 && minor >= 9) return (found = { cmd: [exe, ...pre], version: `${major}.${minor}` });
  }
  found = null;
  findPython.error = tried.length
    ? `Python 3.9 or later is required; found ${tried.join(', ')}.`
    : 'Python 3.9 or later is required and was not found (tried python3, python, py -3; set L2M_PYTHON to override).';
  return found;
}

function requirePython() {
  const py = findPython();
  if (!py) {
    console.error(`l2m: ${findPython.error}\nInstall it from https://www.python.org/downloads/ (or brew/apt/winget install python3).`);
    process.exit(127);
  }
  return py;
}

/** Run a bundled script with inherited stdio; returns the exit code. */
export function runScript(name, args, { cwd = process.cwd(), quiet = false } = {}) {
  const py = requirePython();
  const r = spawnSync(py.cmd[0], [...py.cmd.slice(1), SCRIPTS[name], ...args], {
    cwd, stdio: quiet ? ['ignore', 'pipe', 'pipe'] : 'inherit', encoding: 'utf8',
  });
  if (r.error) throw r.error;
  if (quiet && r.status !== 0) process.stderr.write(r.stdout + r.stderr);
  return r.status ?? 1;
}

/** Run a bundled script and capture its output. */
export function captureScript(name, args, { cwd = process.cwd() } = {}) {
  const py = requirePython();
  const r = spawnSync(py.cmd[0], [...py.cmd.slice(1), SCRIPTS[name], ...args], { cwd, encoding: 'utf8' });
  if (r.error) throw r.error;
  return { status: r.status ?? 1, stdout: r.stdout, stderr: r.stderr };
}
