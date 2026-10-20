# Copilot instructions

This repository uses three Agent Skills in `.claude/skills/`. Copilot loads them automatically: `legacy-code-analysis`,
`requirements-docs` and `mainframe-modernization`. Use them for any analysis of legacy code and for every BRD, FRD,
SRD, RTM or gap report. Don't write these documents freehand.

## Where requirements live

```
docs/requirements/
  PROJECT-CONTEXT.md          one per repository: owner, users, repo URL + commit, constraints
  INDEX.md                    generated catalogue (docver.py index); never edit by hand
  <module>/<feature>/         kebab-case, e.g. accounts/account-update/
    BRD.md  FRD.md  SRD.md    created by docver.py new-feature; RTM.md / GAP-REPORT.md when assessed
    history/                  previous versions (created by docver.py bump)
docs/analysis/                legacy-code-analysis output (inventory, program cards, rules, findings)
```

Start a feature with:
`python3 .claude/skills/requirements-docs/scripts/docver.py new-feature --module <module> --feature <feature> [--component <component>]`

## Non-negotiable rules

- Keep the template's numbered sections exactly. A section that doesn't apply says `N/A: <reason>`.
- Never invent facts, numbers, owners, approvals, test results or deployments. Write `Unknown`, or
  `TBD (decision needed: …, owner: …)`, and add an open question.
- Every BR/FR/SR states its **Basis**: Confirmed, Derived from code (candidate), Assumption or Proposed. Rules recovered from code
  stay `Validation status: Candidate` until a business SME confirms them.
- Evidence is a hyperlink to the exact source lines: write `path:line`, then run `docver.py linkify`. Never paste source code into a document.
- IDs (BR-001, FR-001, SR-001, …) are permanent and local to the feature folder. Never renumber; retire instead.
- Changing an existing document: run `docver.py bump <doc> --summary "…" --sections "…"` **before** editing. Then run
  `linkify`, `trace <folder> --inject`, `validate <folder>` and `index docs/requirements`.
- Don't change a requirement to match what the code does; record the gap in the RTM.

CI runs `docver.py check docs/requirements` on every pull request that touches `docs/requirements/`.
