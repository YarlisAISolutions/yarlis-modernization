---
doc_type: RTM
doc_id: RTM-USER-ADMIN-SIGN-ON
title: "CardDemo: Sign-on and Add User: Requirements Traceability Matrix and Implementation Status"
project: "CardDemo: Sign-on and Add User"
owner: "Demo owner"
version: 0.1.0
status: Draft
last_updated: 2026-11-05
authors: ["Claude (draft)"]
derived_from: [{"doc_id": "SRD-USER-ADMIN-SIGN-ON", "doc_type": "SRD", "version": "0.1.0", "path": "SRD.md"}, {"doc_id": "FRD-USER-ADMIN-SIGN-ON", "doc_type": "FRD", "version": "0.1.0", "path": "FRD.md"}, {"doc_id": "BRD-USER-ADMIN-SIGN-ON", "doc_type": "BRD", "version": "0.1.0", "path": "BRD.md"}]
assessed_ref: "59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e"
module: "user-admin"
feature: "sign-on"
---

# CardDemo: Sign-on and Add User: Requirements Traceability Matrix and Implementation Status

<!-- One row per BR, RUL, FR, SR, NFR, IFR and DR. `docver.py rtm sync` creates and refreshes the rows from the
documents (ID, source, summary, priority, related) and keeps your assessment columns. Fill the assessment columns
from evidence only: links to files/symbols/endpoints/migrations/tests/CI runs/releases. Code, verification
and deployment are separate judgements. -->

## 1. Document Control

### 1.1 Revision History

| Version | Date | Author | Change summary | Sections changed |
|---|---|---|---|---|
| 0.1.0 | 2026-11-05 | Claude (draft) | Initial matrix | All |

## 2. Assessment Scope and Evidence Inspected

<!-- Date, repository, branch/tag/commit (link), and what was inspected: requirements, docs, source, config,
schema/migrations, API definitions, UI, tests, CI/CD workflows, deployment config. List what could NOT be inspected
and which rows that makes Not verifiable. -->

**This is a baseline assessment.** The repository assessed holds only the legacy system, so "Implemented" means the legacy
system already does this (behaviour to reproduce or deliberately change), not migrated.

- Date: 2026-11-05. Repository: https://github.com/aws-samples/aws-mainframe-modernization-carddemo at `59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e`.
- Inspected: the slice's programs, maps and copybooks (`cbl/COSGN00C.cbl`, `cbl/COUSR01C.cbl`, `bms/COSGN00.bms`,
  `bms/COUSR01.bms`, `cpy/CSUSR01Y.cpy`, `cpy/COCOM01Y.cpy`), the load job `jcl/DUSRSECJ.jcl` and the CSD definitions.
- Not available: test suites, CI runs and deployment records for CardDemo. Verification is therefore Not verified on every
  row, and the runtime status of legacy behaviour is Not verifiable. No target (React or Spring Boot) code exists yet, so
  SRD rows are Not implemented and Not deployed.

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
| BR-001 | BRD v0.1.0 | Sign on with a user ID and password | Unknown | BO-01, BO-03, FR-001, FR-002, FR-004, NFR-001, NFR-002, NFR-003, RUL-001, RUL-002, RUL-003, UC-01, UC-02 | Implemented | [`cbl/COSGN00C.cbl:108-140`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COSGN00C.cbl#L108-L140) PROCESS-ENTER-KEY; [`cbl/COSGN00C.cbl:209-257`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COSGN00C.cbl#L209-L257) READ-USER-SEC-FILE | Not verified | No automated test for this path in CardDemo | Not verifiable | Baseline: legacy behaviour to reproduce | SME confirms RUL-001 to RUL-003 | High: one code path |
| BR-002 | BRD v0.1.0 | Route each user to the menu for their role | Unknown | BO-01, BO-03, FR-003, RUL-004, UC-01 | Implemented | [`cbl/COSGN00C.cbl:230-240`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COSGN00C.cbl#L230-L240) | Not verified | No automated test for this path in CardDemo | Not verifiable | Baseline: legacy behaviour to reproduce | SME confirms RUL-004 | High: single IF |
| BR-003 | BRD v0.1.0 | Add a user | Unknown | BO-02, FR-005, FR-006, FR-007, FR-009, RUL-005, RUL-006, RUL-007, UC-03 | Partially implemented | [`cbl/COUSR01C.cbl:115-160`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COUSR01C.cbl#L115-L160) PROCESS-ENTER-KEY; [`cbl/COUSR01C.cbl:238-274`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COUSR01C.cbl#L238-L274) WRITE-USER-SEC-FILE | Not verified | No automated test for this path in CardDemo | Not verifiable | Any user type is accepted (RUL-006) | Decide RUL-006 (Product Owner) | High: explicit checks read |
| BR-004 | BRD v0.1.0 | A new user can sign on at once | Unknown | BO-02, FR-008, RUL-003, UC-03 | Not implemented | [`cbl/COUSR01C.cbl:154-158`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COUSR01C.cbl#L154-L158); [`cbl/COSGN00C.cbl:132-136`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COSGN00C.cbl#L132-L136) | Not verified | No automated test for this path in CardDemo | Not verifiable | Lower-case credentials are saved but never match at sign-on | Decide the case rule, Q-02 (Security Officer) | High: both code paths read |
| BR-005 | BRD v0.1.0 | Existing users keep their access at cutover | Unknown | BO-01, FR-010 | Not implemented | — | Not verified | No automated test for this path in CardDemo | Not verifiable | Transition requirement: no migration tooling yet | Build the SR-007 load job | High: nothing to migrate with yet |
| RUL-001 | BRD v0.1.0 | Both credentials are required | Unknown | BR-001, FR-001 | Implemented | [`cbl/COSGN00C.cbl:117-130`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COSGN00C.cbl#L117-L130) | Not verified | No automated test for this path in CardDemo | Not verifiable | — | SME confirmation | High: explicit EVALUATE |
| RUL-002 | BRD v0.1.0 | Unknown user and wrong password are told apart | Unknown | BR-001, FR-002 | Implemented | [`cbl/COSGN00C.cbl:241-251`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COSGN00C.cbl#L241-L251) | Not verified | No automated test for this path in CardDemo | Not verifiable | — | SME confirmation; Q-12 | High: explicit messages |
| RUL-003 | BRD v0.1.0 | Credentials are compared in upper case | Unknown | BR-001, BR-004, FR-002, FR-008 | Implemented | [`cbl/COSGN00C.cbl:132-136`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COSGN00C.cbl#L132-L136); [`cbl/COSGN00C.cbl:223`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COSGN00C.cbl#L223) | Not verified | No automated test for this path in CardDemo | Not verifiable | Applied at sign-on only, not when adding a user | Decide Q-02 | High: explicit UPPER-CASE |
| RUL-004 | BRD v0.1.0 | Administrators get the administration menu | Unknown | BR-002, FR-003 | Implemented | [`cbl/COSGN00C.cbl:230-240`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COSGN00C.cbl#L230-L240) | Not verified | No automated test for this path in CardDemo | Not verifiable | — | SME confirmation | High: single IF |
| RUL-005 | BRD v0.1.0 | All five user details are required | Unknown | BR-003, FR-005 | Implemented | [`cbl/COUSR01C.cbl:117-151`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COUSR01C.cbl#L117-L151) | Not verified | No automated test for this path in CardDemo | Not verifiable | — | SME confirmation | High: explicit EVALUATE |
| RUL-006 | BRD v0.1.0 | The user type is Administrator or Regular user | Unknown | BR-003, FR-006, FR-010, RSK-04 | Partially implemented | [`cbl/COUSR01C.cbl:142-147`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COUSR01C.cbl#L142-L147) | Not verified | No automated test for this path in CardDemo | Not verifiable | Only presence is checked, not A or U | Decide RUL-006 (Product Owner) | Medium: allowed values come from the screen label |
| RUL-007 | BRD v0.1.0 | A user ID is unique | Unknown | BR-003, DR-001, FR-007 | Implemented | [`cbl/COUSR01C.cbl:260-266`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COUSR01C.cbl#L260-L266) | Not verified | No automated test for this path in CardDemo | Not verifiable | — | SME confirmation | High: DUPKEY/DUPREC handled |
| FR-001 | FRD v0.1.0 | Require both credentials | Unknown | BR-001, MSG-001, MSG-002, RUL-001, SR-001 | Implemented | [`cbl/COSGN00C.cbl:117-130`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COSGN00C.cbl#L117-L130) | Not verified | No automated test for this path in CardDemo | Not verifiable | — | Port with equivalence test | High: explicit checks |
| FR-002 | FRD v0.1.0 | Verify credentials against the register | Unknown | BR-001, FR-003, IFR-001, MSG-003, MSG-004, MSG-005, RUL-002, RUL-003, SR-002 | Implemented | [`cbl/COSGN00C.cbl:209-257`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COSGN00C.cbl#L209-L257) | Not verified | No automated test for this path in CardDemo | Not verifiable | — | Port; decide Q-02 and Q-12 | High: one code path |
| FR-003 | FRD v0.1.0 | Open the menu for the user's role | Unknown | BR-002, FR-002, IFR-001, RUL-004, SR-003 | Implemented | [`cbl/COSGN00C.cbl:224-240`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COSGN00C.cbl#L224-L240) | Not verified | No automated test for this path in CardDemo | Not verifiable | — | Port | High: single IF |
| FR-004 | FRD v0.1.0 | Leave from the sign-on screen | Unknown | BR-001, MSG-014, MSG-015, SR-003 | Implemented | [`cbl/COSGN00C.cbl:85-95`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COSGN00C.cbl#L85-L95) | Not verified | No automated test for this path in CardDemo | Not verifiable | — | Port | High: explicit EVALUATE EIBAID |
| FR-005 | FRD v0.1.0 | Require all user details | Unknown | BR-003, FR-007, MSG-006, MSG-007, MSG-008, MSG-009, MSG-010, RUL-005, SR-004 | Implemented | [`cbl/COUSR01C.cbl:117-151`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COUSR01C.cbl#L117-L151) | Not verified | No automated test for this path in CardDemo | Not verifiable | — | Port | High: explicit EVALUATE |
| FR-006 | FRD v0.1.0 | Accept only the two roles | Unknown | BR-003, DR-001, FR-007, MSG-016, RUL-006, SR-004 | Not implemented | [`cbl/COUSR01C.cbl:142-147`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COUSR01C.cbl#L142-L147) | Not verified | No automated test for this path in CardDemo | Not verifiable | Deliberate change: legacy accepts any character | Implement in target | High: only presence checked |
| FR-007 | FRD v0.1.0 | Save a new user with a unique user ID | Unknown | BR-003, DR-001, FR-005, FR-006, FR-008, IFR-002, MSG-011, MSG-012, MSG-013, RUL-007, SR-004, SR-006 | Implemented | [`cbl/COUSR01C.cbl:238-274`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COUSR01C.cbl#L238-L274) | Not verified | No automated test for this path in CardDemo | Not verifiable | — | Port | High: explicit RESP handling |
| FR-008 | FRD v0.1.0 | New credentials sign on as entered | Unknown | BR-004, FR-007, RUL-003, SR-005 | Not implemented | [`cbl/COUSR01C.cbl:154-158`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COUSR01C.cbl#L154-L158); [`cbl/COSGN00C.cbl:132-136`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COSGN00C.cbl#L132-L136) | Not verified | No automated test for this path in CardDemo | Not verifiable | Deliberate change: legacy fails for lower-case input | Implement SR-005 after Q-02 | High: both code paths read |
| FR-009 | FRD v0.1.0 | Clear the form and go back | Unknown | BR-003, MSG-015, SR-008 | Partially implemented | [`cbl/COUSR01C.cbl:90-103`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COUSR01C.cbl#L90-L103); [`cbl/COUSR01C.cbl:279-295`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cbl/COUSR01C.cbl#L279-L295) | Not verified | No automated test for this path in CardDemo | Not verifiable | Clear and Back work; the screen also shows F12=Exit, which is not handled | Decide Q-07 | High: explicit EVALUATE EIBAID |
| FR-010 | FRD v0.1.0 | Migrate existing users | Unknown | BR-005, RUL-006, SR-007 | Not implemented | — | Not verified | No automated test for this path in CardDemo | Not verifiable | Transition requirement | Build SR-007 | High |
| SR-001 | SRD v0.1.0 | Reject incomplete sign-on requests | Unknown | FR-001, MSG-001, MSG-002 | Not implemented | — | Not verified | — | Not deployed | Target-state requirement: no React or Spring Boot code exists yet | Build in the target wave | High: baseline assessment, legacy-only repository |
| SR-002 | SRD v0.1.0 | Check credentials against APP_USER | Unknown | FR-002, MSG-003, MSG-004, MSG-005 | Not implemented | — | Not verified | — | Not deployed | Target-state requirement: no React or Spring Boot code exists yet | Build in the target wave | High: baseline assessment, legacy-only repository |
| SR-003 | SRD v0.1.0 | Issue a session carrying the role | Unknown | FR-003, FR-004 | Not implemented | — | Not verified | — | Not deployed | Target-state requirement: no React or Spring Boot code exists yet | Build in the target wave | High: baseline assessment, legacy-only repository |
| SR-004 | SRD v0.1.0 | Create users with validation | Unknown | FR-005, FR-006, FR-007, MSG-006, MSG-007, MSG-008, MSG-009, MSG-010, MSG-012, MSG-016 | Not implemented | — | Not verified | — | Not deployed | Target-state requirement: no React or Spring Boot code exists yet | Build in the target wave | High: baseline assessment, legacy-only repository |
| SR-005 | SRD v0.1.0 | Store credentials under one normalisation rule | Unknown | FR-008 | Not implemented | — | Not verified | — | Not deployed | Target-state requirement: no React or Spring Boot code exists yet | Build in the target wave | High: baseline assessment, legacy-only repository |
| SR-006 | SRD v0.1.0 | Restrict user creation to administrators | Unknown | FR-007 | Not implemented | — | Not verified | — | Not deployed | Target-state requirement: no React or Spring Boot code exists yet | Build in the target wave | High: baseline assessment, legacy-only repository |
| SR-007 | SRD v0.1.0 | Load the legacy register | Unknown | FR-010 | Not implemented | — | Not verified | — | Not deployed | Target-state requirement: no React or Spring Boot code exists yet | Build in the target wave | High: baseline assessment, legacy-only repository |
| SR-008 | SRD v0.1.0 | Clear and back are client-only | Unknown | FR-009 | Not implemented | — | Not verified | — | Not deployed | Target-state requirement: no React or Spring Boot code exists yet | Build in the target wave | High: baseline assessment, legacy-only repository |
| NFR-001 | SRD v0.1.0 | Passwords are never stored readable | Unknown | BR-001 | Not implemented | — | Not verified | — | Not deployed | Target-state; legacy stores passwords readable ([`cpy/CSUSR01Y.cpy:21`](https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/app/cpy/CSUSR01Y.cpy#L21)) | Build in the target wave | High: baseline assessment, legacy-only repository |
| NFR-002 | SRD v0.1.0 | Failed sign-on limit | Unknown | BR-001 | Not implemented | — | Not verified | — | Not deployed | Target-state; legacy has no attempt limit; limit TBD (Q-03) | Build in the target wave | High: baseline assessment, legacy-only repository |
| NFR-003 | SRD v0.1.0 | Sign-on response time | Unknown | BR-001 | Not implemented | — | Not verified | — | Not deployed | Target-state requirement: no React or Spring Boot code exists yet | Build in the target wave | High: baseline assessment, legacy-only repository |
| IFR-001 | SRD v0.1.0 | Session API | Unknown | FR-002, FR-003 | Not implemented | — | Not verified | — | Not deployed | Target-state requirement: no React or Spring Boot code exists yet | Build in the target wave | High: baseline assessment, legacy-only repository |
| IFR-002 | SRD v0.1.0 | User creation API | Unknown | FR-007 | Not implemented | — | Not verified | — | Not deployed | Target-state requirement: no React or Spring Boot code exists yet | Build in the target wave | High: baseline assessment, legacy-only repository |
| DR-001 | SRD v0.1.0 | APP_USER table | Unknown | FR-006, FR-007, RUL-007 | Not implemented | — | Not verified | — | Not deployed | Target-state requirement: no React or Spring Boot code exists yet | Build in the target wave | High: baseline assessment, legacy-only repository |
<!-- rtm:end -->

### 4.1 Summary

<!-- summary:begin -->
**Code implementation status by document and kind**

| Document / kind | Implemented | Partially implemented | Not implemented | Blocked | Not applicable | Not verifiable | Not assessed | Total |
|---|---|---|---|---|---|---|---|---|
| BRD business requirements (BR) | 2 | 1 | 2 | 0 | 0 | 0 | 0 | 5 |
| BRD business rules (RUL) | 6 | 1 | 0 | 0 | 0 | 0 | 0 | 7 |
| FRD functional requirements (FR) | 6 | 1 | 3 | 0 | 0 | 0 | 0 | 10 |
| SRD system requirements (SR/NFR/IFR/DR) | 0 | 0 | 14 | 0 | 0 | 0 | 0 | 14 |
| **All** | 14 | 3 | 19 | 0 | 0 | 0 | 0 | 36 |

**Verification status:** Verified 0, Partially verified 0, Not verified 36, Not verifiable 0, Not assessed 0

**Runtime/deployment status:** Deployed 0, Partially deployed 0, Not deployed 14, Not verifiable 22, Not assessed 0
<!-- summary:end -->

## 5. Conflicts and Duplicates

<!-- Requirements that contradict or duplicate each other, or code behaviour that contradicts a requirement;
recommend a resolution. Do not change the requirement to match the code silently. -->

- RUL-003 (credentials compared in upper case) conflicts with how Add User saves credentials (as typed): BR-004 and FR-008
  are Not implemented for that reason. Resolution needs BRD Q-02; the requirement is not changed to match the code.
- RUL-006 (two roles) is stated by the screen label but not enforced: FR-006 is a deliberate change.

## 6. Open Questions and Decisions Needed

| # | Question / decision | Owner | Due | Answer / decision |
|---|---|---|---|---|
| Q-02 | Case rule and migration of passwords (BRD) | Security Officer | Unknown | |
| Q-07 | Exit key on Add User (FRD) | Product Owner | Unknown | |

