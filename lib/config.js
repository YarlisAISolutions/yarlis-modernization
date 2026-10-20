// l2m.config.json: the project's inputs (source, documents, schema), folders and default agent. Plain JSON, no
// dependencies. Every field can be overridden by a command-line flag.
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';

export const CONFIG_FILE = 'l2m.config.json';

const LISTS = ['source', 'docs', 'schema'];
const STRINGS = ['project', 'owner', 'targetStack', 'migrationStrategy', 'analysisDir', 'requirementsDir', 'agent'];

export function defaultConfig({ project, src, owner, targetStack, agent = 'claude' } = {}) {
  return {
    $schema: 'https://raw.githubusercontent.com/YarlisAISolutions/yarlis-modernization/main/l2m.config.schema.json',
    project: project || 'Unknown',
    owner: owner || 'Unknown',
    source: src ? [src] : [],
    docs: ['docs/inputs'],
    schema: [],
    targetStack: targetStack || 'Unknown',
    migrationStrategy: 'Unknown',
    analysisDir: 'docs/analysis',
    requirementsDir: 'docs/requirements',
    agent,
    agents: {},
  };
}

/** Find l2m.config.json in dir or a parent. Returns { path, root, config } or null. */
export function findConfig(dir = process.cwd()) {
  for (let d = resolve(dir); ; d = dirname(d)) {
    const p = join(d, CONFIG_FILE);
    if (existsSync(p)) return { path: p, root: d, config: loadConfig(p) };
    if (dirname(d) === d) return null;
  }
}

export function loadConfig(path) {
  let raw;
  try {
    raw = JSON.parse(readFileSync(path, 'utf8'));
  } catch (e) {
    throw new Error(`${path}: ${e.message}`);
  }
  return validateConfig(raw, path);
}

export function validateConfig(raw, where = CONFIG_FILE) {
  if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) throw new Error(`${where}: must be a JSON object`);
  const cfg = { ...defaultConfig(), ...raw };
  for (const k of LISTS) {
    if (typeof cfg[k] === 'string') cfg[k] = [cfg[k]];
    if (!Array.isArray(cfg[k]) || cfg[k].some((v) => typeof v !== 'string')) throw new Error(`${where}: "${k}" must be a string or a list of strings`);
  }
  for (const k of STRINGS) if (typeof cfg[k] !== 'string') throw new Error(`${where}: "${k}" must be a string`);
  if (typeof cfg.agents !== 'object' || Array.isArray(cfg.agents)) throw new Error(`${where}: "agents" must be an object`);
  for (const [name, a] of Object.entries(cfg.agents)) {
    if (!Array.isArray(a.cmd) || !a.cmd.length || a.cmd.some((v) => typeof v !== 'string')) {
      throw new Error(`${where}: agents.${name}.cmd must be a non-empty list of strings`);
    }
  }
  return cfg;
}
