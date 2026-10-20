// `l2m doctor`: is this machine and this repository ready for l2m?
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { BUILTIN, available } from './agents.js';
import { findConfig } from './config.js';
import { SKILLS } from './install.js';
import { PKG_ROOT, VERSION, findPython } from './python.js';

function same(a, b) {
  return existsSync(a) && existsSync(b) && readFileSync(a).equals(readFileSync(b));
}

export function doctor(log = console.log) {
  let failed = 0;
  const line = (ok, label, detail = '') => { if (ok === false) failed++; log(`${ok === true ? 'ok  ' : ok === false ? 'FAIL' : 'warn'} ${label}${detail ? `: ${detail}` : ''}`); };

  log(`l2m ${VERSION} (${PKG_ROOT})\n`);
  const major = Number(process.versions.node.split('.')[0]);
  line(major >= 22 || null, 'Node', `${process.versions.node}${major < 22 ? ' (22 or later is supported)' : ''}`);
  const py = findPython();
  line(py ? true : false, 'Python 3.9+', py ? `${py.cmd.join(' ')} ${py.version}` : findPython.error);
  const g = spawnSync('git', ['--version'], { encoding: 'utf8' });
  line(g.status === 0 || null, 'git', g.status === 0 ? g.stdout.trim() : 'not found: evidence permalinks, schema-diff and bumpcheck need it');
  for (const [name, a] of Object.entries(BUILTIN)) line(available(a.cmd) || null, `agent ${name}`, available(a.cmd) ? a.cmd[0] : `${a.cmd[0]} not on PATH (l2m generate --agent ${name} will print the prompt instead)`);

  log('');
  const found = findConfig();
  if (!found) {
    line(null, 'repository', 'no l2m.config.json here or above: run `l2m init`');
  } else {
    line(true, 'config', found.path);
    const root = found.root;
    for (const s of SKILLS) {
      const ok = existsSync(join(root, '.claude/skills', s, 'SKILL.md'));
      const drift = ok && !same(join(root, '.claude/skills', s, 'SKILL.md'), join(PKG_ROOT, '.claude/skills', s, 'SKILL.md'));
      line(ok ? (drift ? null : true) : false, `skill ${s}`, !ok ? 'missing: run `l2m init`' : drift ? 'differs from this l2m version: `l2m init --upgrade` refreshes it' : '');
    }
    const vf = join(root, '.claude/skills/.l2m-version');
    const installed = existsSync(vf) ? readFileSync(vf, 'utf8').trim() : null;
    line(installed === VERSION || null, 'kit version', installed ? `${installed}${installed !== VERSION ? ` (CLI is ${VERSION})` : ''}` : 'unknown');
    for (const s of found.config.source) line(existsSync(join(root, s)) || false, `source ${s}`, existsSync(join(root, s)) ? '' : 'not found');
  }
  log(failed ? `\n${failed} problem(s) found.` : '\nReady.');
  return failed ? 1 : 0;
}
