---
description: Scan legacy source and build the analysis knowledge base for a slice
agent: agent
argument-hint: src=<path> roots=<TRANSIDs/jobs/programs>
---

Use the `legacy-code-analysis` skill. Follow [prompts/01-analyze-legacy-code.md](../../prompts/01-analyze-legacy-code.md).

- Source: ${input:src:path to the legacy source root}
- Slice roots: ${input:roots:transaction IDs, job names or program names}

Steps: `inventory.py scan --src <src> --out docs/analysis`, close the unresolved references,
`inventory.py slice --root <roots>`, then read the files and write `system-overview.md`, `rules/<domain>.md`, `findings.md`
and `analysis-notes.md`. Evidence is linked (`docver.py linkify docs/analysis --context docs/requirements/PROJECT-CONTEXT.md`).
Report: counts, unresolved references left, rules and findings found, and open questions.
