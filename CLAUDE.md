# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Three Claude Code skills (in `.claude/skills/`) for legacy modernization. Each one is a `SKILL.md`, a stdlib-only Python script, and references:
- `legacy-code-analysis`: `scripts/inventory.py` (`scan`, `slice`, `domains`) builds `docs/analysis/`.
- `requirements-docs`: `scripts/docver.py` (`init`, `bump`, `validate`, `linkify`, `trace`, `rtm`, `status`, `diff`);
  `assets/templates/` hold the standard BRD/FRD/SRD/RTM/GAP/CONTEXT structures, and `validate` reads the section list from them.
- `mainframe-modernization`: `scripts/mapgen.py` drafts the legacy → React/Spring Boot/DB2 mapping from `inventory.json`.

`prompts/` holds the standard prompt structure and per-step templates. `docs/images/` holds the hand-written SVG logo and cartoons.

## Working on the skills

- Changing a template's `## N. Title` headings changes what `validate` enforces. Update `REQUIRED_DIAGRAMS` in
  `docver.py`, `references/diagrams.md` and `references/writing-guide.md` to the same section numbers.
- Keep the scripts dependency-free (Python 3.9+ standard library).
- Run `bash tests/selftest.sh` after any script change (CI runs it on Python 3.9 and 3.12). Add an assertion for every bug fixed.
- The Copilot kit (`.github/`, `AGENTS.md`) is what `scripts/install.sh` copies into adopting repos. Keep it consistent with the skills.
- Test against AWS CardDemo (clone https://github.com/aws-samples/aws-mainframe-modernization-carddemo outside this repo):
  `inventory.py scan --src <carddemo>/app --out /tmp/an` should report 0 unresolved references; then exercise
  `docver.py init/bump/linkify/trace/validate/rtm` on a scratch `docs/requirements`.
- Documents cite evidence as `path:line` turned into links by `docver.py linkify`. Never paste legacy source into templates or examples.
- `skill-evals/` is local eval output and is git-ignored.
