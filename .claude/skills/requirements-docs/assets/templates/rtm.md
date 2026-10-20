---
doc_type: RTM
doc_id: {{DOC_ID}}
title: "{{PROJECT}}: Requirements Traceability Matrix and Implementation Status"
project: "{{PROJECT}}"
owner: "{{OWNER}}"
version: 0.1.0
status: Draft
last_updated: {{DATE}}
authors: ["{{AUTHOR}}"]
derived_from: {{DERIVED_FROM}}
assessed_ref: "{{REPO_REF}}"
---

# {{PROJECT}}: Requirements Traceability Matrix and Implementation Status

<!-- One row per BR, RUL, FR, SR, NFR, IFR and DR. `docver.py rtm sync` creates and refreshes the rows from the
documents (ID, source, summary, priority, related) and keeps your assessment columns. Fill the assessment columns
from evidence only: links to files/symbols/endpoints/migrations/tests/CI runs/releases. Code, verification
and deployment are separate judgements. -->

## 1. Document Control

### 1.1 Revision History

| Version | Date | Author | Change summary | Sections changed |
|---|---|---|---|---|
| 0.1.0 | {{DATE}} | {{AUTHOR}} | Initial matrix | All |

## 2. Assessment Scope and Evidence Inspected

<!-- Date, repository, branch/tag/commit (link), and what was inspected: requirements, docs, source, config,
schema/migrations, API definitions, UI, tests, CI/CD workflows, deployment config. List what could NOT be inspected
and which rows that makes Not verifiable. -->

## 3. Status Definitions

| Status | Meaning |
|---|---|
| Implemented | Code evidence covers the stated requirement. It doesn't mean tested or deployed. |
| Partially implemented | Some behaviour exists; one or more acceptance criteria or flows are missing. |
| Not implemented | No supporting implementation found after inspecting the available source. |
| Blocked | Depends on an identified unresolved dependency or decision (named in Next action). |
| Not applicable | Out of scope for this codebase, or the requirement is retired. |
| Not verifiable | The available code, tests or environment don't give enough evidence to decide. |
| Not assessed | Row not yet reviewed (temporary; not allowed in an Approved matrix). |

Verification: Verified, Partially verified, Not verified, Not verifiable. Runtime/deployment: Deployed, Partially deployed,
Not deployed, Not verifiable. Mocks, placeholders, TODOs, stubs, feature-flagged-off and untested paths count as incomplete
unless evidence shows they satisfy the requirement. A UI element alone is not proof of a working capability. Don't claim
Deployed without deployment evidence.

## 4. Traceability and Implementation Matrix

<!-- Columns are fixed. Escape a literal pipe inside a cell as \|. Confidence: High | Medium | Low + short reason. -->

<!-- rtm:begin -->
| ID | Source | Summary | Priority | Related | Code status | Code evidence | Verification status | Verification evidence | Runtime status | Gap / remaining work | Next action | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
<!-- rtm:end -->

### 4.1 Summary

<!-- summary:begin -->
<!-- summary:end -->

## 5. Conflicts and Duplicates

<!-- Requirements that contradict or duplicate each other, or code behaviour that contradicts a requirement;
recommend a resolution. Do not change the requirement to match the code silently. -->

## 6. Open Questions and Decisions Needed

| # | Question / decision | Owner | Due | Answer / decision |
|---|---|---|---|---|
