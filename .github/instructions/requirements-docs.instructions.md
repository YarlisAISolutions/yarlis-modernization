---
applyTo: "docs/requirements/**/*.md"
description: Rules for editing BRD/FRD/SRD/RTM/GAP documents
---

You are editing a versioned requirements document. Follow `.claude/skills/requirements-docs/SKILL.md`.

- Before changing content, run `python3 .claude/skills/requirements-docs/scripts/docver.py bump <this file> --summary "<what and why>" --sections "<numbers>"`.
  Exception: version 0.1.0 while it is first being filled.
- Don't edit `INDEX.md`, anything under `history/`, or the blocks between `<!-- trace:begin -->`/`<!-- rtm:begin -->`/`<!-- summary:begin -->` markers.
  Scripts regenerate them.
- Keep section numbers and titles; use `N/A: <reason>` instead of deleting.
- New requirements take the next free ID in this feature folder. Each one carries Basis, Priority (or `Unknown (proposed: X)`) and,
  for FR/SR, a `Traces to:` line.
- Evidence: `path:line` or `path:start-end` per reference, converted by `docver.py linkify`. No pasted code.
- Diagrams are Mermaid. Quote labels that contain `(` or `:`, and don't use `end` as a node id.
- Finish with: `docver.py linkify <folder> && docver.py trace <folder> --inject && docver.py validate <folder> && docver.py index docs/requirements`.
