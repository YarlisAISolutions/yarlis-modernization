# l2m CLI reference and 1.0 contract

Every command, flag, `l2m.config.json` key and exit code of `l2m` (`@l2m/cli`). Each one is **stable** or **experimental**:

- **Stable**: from 1.0.0 on, it is not removed or renamed and keeps its type and meaning until 2.0. New optional flags and keys can be added in a minor release.
- **Experimental**: built and tested, but it may change or go away in a minor release. Pin the exact version if you script against it.

The contract is machine-readable in [`test/cli-contract.json`](../test/cli-contract.json). `npm test` runs [`test/contract.test.js`](../test/contract.test.js), which fails when:

- a stable command, alias, generate step, flag or config key is removed or renamed, or a flag changes type;
- a new command, step, flag or config key is not classified in the contract and in this page;
- `l2m --help` or `l2m.config.schema.json` differs from its snapshot in [`test/snapshots/`](../test/snapshots/);
- an exit code changes;
- this page and the contract disagree.

Help text wording is part of the snapshot, so a change to it needs a snapshot update too. The version number is left out of the snapshot.

## Changing the contract

1. Make the change, and add or move the item in `test/cli-contract.json` and in the tables below.
2. A stable item can only be removed, renamed or retyped in a major release. Promoting an experimental item to stable is fine in a minor release.
3. Run `L2M_UPDATE_SNAPSHOTS=1 npm test` to refresh `test/snapshots/`, then `npm test`.
4. Add a line under [Contract changes](#contract-changes).

## Commands

### Commands

| Command | Status | What it does |
|---|---|---|
| `init [dir]` | stable | Installs the skills, `prompts/`, the agent kit, `l2m.config.json`, `docs/inputs/` and `PROJECT-CONTEXT.md` into a repository. |
| `doctor` | stable | Checks Node, Python 3.9+, git, the agent CLIs and, inside a repository, the installed kit. |
| `analyze <cmd> …` | stable | Runs `inventory.py`; arguments go to the script unchanged. |
| `map …` | stable | Runs `mapgen.py` (`--inventory`, `--out`, `--data-out`, `--programs`); arguments go to the script unchanged. |
| `docs <cmd> …` | stable | Runs `docver.py`; arguments go to the script unchanged. |
| `generate <step>` | stable | Prepares inputs, scaffolds the feature folder, runs the agent, then `linkify`, `trace --inject`, `validate` and `index`. |
| `prompt <step>` | stable | Prints the filled prompt for a step instead of running an agent. Same flags as `generate`. |
| `help` | stable | Prints the help text. Aliases `-h`, `--help`, and no command at all. |
| `version` | stable | Prints the version. Aliases `-v`, `--version`. |

### Generate steps

| Step | Status | Notes |
|---|---|---|
| `analysis` | stable | Needs `--scope`. |
| `brd` | stable | Needs `--scope`. |
| `frd` | stable | Derived from the BRD. |
| `srd` | stable | Derived from the FRD and the mapgen drafts. |
| `all` | stable | `brd` → `frd` → `srd`; needs `--scope`. |
| `change-request` | experimental | New in 0.1 and just reworked (MOD-8): the version-bump protocol may still change. |
| `assess` | experimental | The assessment prompt and its output format are still settling. |

### init flags

| Flag | Status | Type |
|---|---|---|
| `--agents <list>` | stable | string: comma-separated `claude,copilot,codex,gemini` |
| `--project <name>` | stable | string |
| `--src <path>` | stable | string |
| `--owner <name>` | stable | string |
| `--target-stack <text>` | stable | string |
| `--force` | stable | boolean |
| `--upgrade` | stable | boolean |
| `--dry-run` | stable | boolean |

### generate and prompt flags

| Flag | Status | Type |
|---|---|---|
| `--module <m>` | stable | string |
| `--feature <f>` | stable | string |
| `--component <c>` | stable | string |
| `--title <text>` | stable | string |
| `--scope <slice>` | stable | string |
| `--out-of-scope <text>` | stable | string |
| `--src <path>` | stable | string, repeatable |
| `--docs <path\|url>` | stable | string, repeatable |
| `--schema <path>` | stable | string, repeatable |
| `--agent <name>` | stable | string |
| `--agent-cmd <cmd>` | stable | string; `{prompt}`, `{prompt_file}`, or stdin when neither is used |
| `--yolo` | stable | boolean |
| `--print` | stable | boolean |
| `--force` | stable | boolean |
| `--no-init` | stable | boolean |
| `--cr <ID>` | experimental | string (change-request) |
| `--summary <text>` | experimental | string (change-request) |
| `--schema-diff <base>[..<head>]` | experimental | string (change-request) |
| `--affects <docs>` | experimental | string (change-request) |
| `--requested-by <name>` | experimental | string (change-request) |
| `--reason <text>` | experimental | string (change-request) |
| `--refs <links>` | experimental | string (change-request) |
| `--author <name>` | experimental | string (change-request) |

### analyze subcommands

`inventory.py`'s own flags are documented by `l2m analyze <cmd> --help`. The subcommand names are part of the contract.

| Subcommand | Status |
|---|---|
| `scan` | stable |
| `slice` | stable |
| `domains` | stable |
| `schema-diff` | stable |

### docs subcommands

`docver.py`'s own flags are documented by `l2m docs <cmd> --help`. The subcommand names are part of the contract; `check` and `bumpcheck` are what the installed `requirements-check.yml` workflow runs.

| Subcommand | Status |
|---|---|
| `init` | stable |
| `new-feature` | stable |
| `bump` | stable |
| `validate` | stable |
| `linkify` | stable |
| `trace` | stable |
| `rtm` | stable |
| `status` | stable |
| `diff` | stable |
| `index` | stable |
| `check` | stable |
| `bumpcheck` | stable |

## Configuration

`l2m.config.json`, found in the current folder or a parent. Schema: [`l2m.config.schema.json`](../l2m.config.schema.json) (snapshotted). Every key is optional; flags win over the file.

### Config keys

| Key | Status | Type | Default (`l2m init`) |
|---|---|---|---|
| `$schema` | stable | string | the schema URL on `main` |
| `project` | stable | string | `Unknown` |
| `owner` | stable | string | `Unknown` |
| `source` | stable | string or list of strings | `[]` (`--src` sets it) |
| `docs` | stable | string or list of strings | `["docs/inputs"]` |
| `schema` | stable | string or list of strings | `[]` |
| `targetStack` | stable | string | `Unknown` |
| `migrationStrategy` | stable | string | `Unknown` |
| `analysisDir` | stable | string | `docs/analysis` |
| `requirementsDir` | stable | string | `docs/requirements` |
| `agent` | stable | string | `claude` |
| `agents` | stable | object: `{ "<name>": { "cmd": [...], "yolo": [...] } }` | `{}` |

## Exit codes

### Exit codes

| Code | Status | Meaning |
|---|---|---|
| `0` | stable | Success. |
| `1` | stable | A check failed: `doctor` found a problem, or `generate`'s validation or version check failed. |
| `2` | stable | Usage error: unknown command, step or flag, or a missing or bad value. |
| `127` | stable | Python 3.9+ was not found (`analyze`, `map`, `docs`, `generate`). |

`analyze`, `map` and `docs` exit with the script's own code. `generate` exits with the agent's code when the agent fails.

## Contract changes

Record every change to a stable or experimental item here, newest first.

- 0.1.0: first contract (MOD-3).
