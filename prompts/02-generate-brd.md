# Prompt: generate the BRD

```markdown
## 1. Role
Act as a senior business analyst and product manager.

## 2. Context
See docs/requirements/PROJECT-CONTEXT.md.

## 3. Task
Write the Business Requirements Document for [CAPABILITY / PRODUCT], version 0.1.0.

## 4. Scope
- Slice: [transactions / jobs / feature]
- In scope: [...]   Out of scope: [...]

## 5. Inputs
- Analysis knowledge base: docs/analysis/ (run the analysis first if it's missing)
- Stakeholder notes / interviews / existing documents: [LINKS or none]

## 6. Deliverables
docs/requirements/<module>/<feature>/BRD.md (standard 21-section structure), scaffolded with `docver.py new-feature --module <module> --feature <feature>`.

## 7. Rules
- Business language only: no technology in requirement statements; code identifiers only inside evidence links.
- Objectives (BO) have KPI, baseline and target, or TBD (decision needed: ..., owner: ...).
- Every BR supports a BO, has a priority (or "Unknown (proposed: X)"), a basis and acceptance criteria.
- Business rules (RUL) carry a linked source, Validation status: Candidate, and a confidence level.
- Required diagrams: as-is process (§7), to-be process (§8), conceptual data model (§12.2).
- Legacy defects and anomalies go to pain points (§7), risks (§15) or open questions (§19).
- Unknowns go to open questions with an owner. Nothing invented.

## 8. Verification and report
Run linkify, trace --inject and validate. Report the IDs created, the validation result, and the top open questions.
```
