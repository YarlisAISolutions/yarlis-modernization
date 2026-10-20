# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Three Claude Code skills (in `.claude/skills/`) for legacy modernization, and the `l2m` CLI that packages them as the
npm package `@l2m/cli`. Each skill is a `SKILL.md`, a stdlib-only Python script, and references:
- `legacy-code-analysis`: `scripts/inventory.py` (`scan`, `slice`, `domains`, `schema-diff`) builds `docs/analysis/`.
- `requirements-docs`: `scripts/docver.py` (`init`, `bump`, `validate`, `linkify`, `trace`, `rtm`, `status`, `diff`);
  `assets/templates/` hold the standard BRD/FRD/SRD/RTM/GAP/CONTEXT structures, and `validate` reads the section list from them.
- `mainframe-modernization`: `scripts/mapgen.py` drafts the legacy → React/Spring Boot/DB2 mapping from `inventory.json`.

`prompts/` holds the standard prompt structure and per-step templates. `docs/images/` holds the hand-written SVG logo and cartoons.

## The l2m CLI (`bin/l2m.js`, `lib/`)

- Node 22+, ESM, **no dependencies or devDependencies** (tests use `node:test`). Keep it that way: nothing for the dep-refresh routine.
- It is a launcher: `analyze`/`map`/`docs` pass arguments straight to the bundled scripts, always from the package's own copy
  (`lib/python.js`), never from a target repo's `.claude/skills`. Put new analysis or document logic in the Python scripts, not in JS.
- `generate` keeps the Role, Deliverables, Rules and Verification blocks of `prompts/0N-*.md` word for word and fills the rest
  (`lib/prompts.js`). Changing a prompt's `## N.` headings or adding a `[PLACEHOLDER]` there needs a matching change in `lib/prompts.js`.
- Agent command templates live in `lib/agents.js`. Check a flag against the agent's `--help` before changing it.
- `lib/install.js` is the installer; `scripts/install.sh` calls it when Node 22+ is present and keeps a bash fallback. Change both.
- npm leaves dotfolders out by default: `files` in `package.json` lists `.claude/skills` and the `.github` kit explicitly.
  `bash scripts/check-pack.sh` checks the package contents.
- Run `npm test` (CLI) and `bash tests/selftest.sh` (scripts) after any change.
- Release: bump `version` in `package.json` and `.claude-plugin/marketplace.json` together (a test checks this). Merging to `main`
  publishes through `.github/workflows/release.yml` (NPM_TOKEN from Yarlis Keep, later trusted publishing).

## Working on the skills

- Changing a template's `## N. Title` headings changes what `validate` enforces. Update `REQUIRED_DIAGRAMS` in
  `docver.py`, `references/diagrams.md` and `references/writing-guide.md` to the same section numbers.
- Keep the scripts dependency-free (Python 3.9+ standard library).
- Run `bash tests/selftest.sh` after any script change (CI runs it on Python 3.9 and 3.12, plus `npm test`). Add an assertion for every bug fixed.
- The Copilot kit (`.github/`, `AGENTS.md`) is what `scripts/install.sh` copies into adopting repos. Keep it consistent with the skills.
- Test against AWS CardDemo (clone https://github.com/aws-samples/aws-mainframe-modernization-carddemo outside this repo):
  `inventory.py scan --src <carddemo>/app --out /tmp/an` should report 0 unresolved references; then exercise
  `docver.py init/bump/linkify/trace/validate/rtm` on a scratch `docs/requirements`.
- Documents cite evidence as `path:line` turned into links by `docver.py linkify`. Never paste legacy source into templates or examples.
- `skill-evals/` is local eval output and is git-ignored.
