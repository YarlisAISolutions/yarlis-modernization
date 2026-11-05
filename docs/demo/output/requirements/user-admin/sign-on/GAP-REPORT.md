---
doc_type: GAP
doc_id: GAP-USER-ADMIN-SIGN-ON
title: "CardDemo: Sign-on and Add User: Executive Progress and Gap Report"
project: "CardDemo: Sign-on and Add User"
owner: "Demo owner"
version: 0.1.0
status: Draft
last_updated: 2026-11-05
authors: ["Claude (draft)"]
derived_from: [{"doc_id": "RTM-USER-ADMIN-SIGN-ON", "doc_type": "RTM", "version": "0.1.0", "path": "RTM.md"}]
assessed_ref: "59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e"
module: "user-admin"
feature: "sign-on"
---

# CardDemo: Sign-on and Add User: Executive Progress and Gap Report

<!-- Two pages for decision makers, built on the RTM. Counts come from `docver.py rtm summary`; everything else
cites RTM row IDs. Separate facts (with evidence), assumptions and recommendations. No completion percentage
unless priorities are agreed; if one is shown, state the formula and exclusions (rtm summary --weighted does). -->

## 1. Document Control

### 1.1 Revision History

| Version | Date | Author | Change summary | Sections changed |
|---|---|---|---|---|
| 0.1.0 | 2026-11-05 | Claude (draft) | Initial report | All |

## 2. Assessment Scope, Date and Evidence

**This is a baseline assessment** of the legacy CardDemo at `59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e` on 2026-11-05: it shows what the legacy system does
today for sign-on and Add User, not migration progress. Evidence inspected and its limits: RTM §2.

## 3. Requirement Counts by Document and Status

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

## 4. Implemented but Not Verified

<!-- unverified:begin -->
| ID | Summary | Code status | Verification status | Next action |
|---|---|---|---|---|
| BR-001 | Sign on with a user ID and password | Implemented | Not verified | SME confirms RUL-001 to RUL-003 |
| BR-002 | Route each user to the menu for their role | Implemented | Not verified | SME confirms RUL-004 |
| BR-003 | Add a user | Partially implemented | Not verified | Decide RUL-006 (Product Owner) |
| RUL-001 | Both credentials are required | Implemented | Not verified | SME confirmation |
| RUL-002 | Unknown user and wrong password are told apart | Implemented | Not verified | SME confirmation; Q-12 |
| RUL-003 | Credentials are compared in upper case | Implemented | Not verified | Decide Q-02 |
| RUL-004 | Administrators get the administration menu | Implemented | Not verified | SME confirmation |
| RUL-005 | All five user details are required | Implemented | Not verified | SME confirmation |
| RUL-006 | The user type is Administrator or Regular user | Partially implemented | Not verified | Decide RUL-006 (Product Owner) |
| RUL-007 | A user ID is unique | Implemented | Not verified | SME confirmation |
| FR-001 | Require both credentials | Implemented | Not verified | Port with equivalence test |
| FR-002 | Verify credentials against the register | Implemented | Not verified | Port; decide Q-02 and Q-12 |
| FR-003 | Open the menu for the user's role | Implemented | Not verified | Port |
| FR-004 | Leave from the sign-on screen | Implemented | Not verified | Port |
| FR-005 | Require all user details | Implemented | Not verified | Port |
| FR-007 | Save a new user with a unique user ID | Implemented | Not verified | Port |
| FR-009 | Clear the form and go back | Partially implemented | Not verified | Decide Q-07 |
<!-- unverified:end -->

## 5. Highest-Impact Gaps and Risks

1. **New users who cannot sign on** (BR-004, FR-008; RSK-01): credentials are saved as typed and checked in upper case.
2. **Readable passwords and a shared default password** (NFR-001; RSK-02): the target must not copy this.
3. **No attempt limit** (NFR-002; RSK-03).
4. **Any character accepted as a role** (RUL-006, FR-006; RSK-04).
5. **No migration tooling yet** for the register (BR-005, FR-010, SR-007).

## 6. Blocking Dependencies and Decisions

- BRD Q-02 (case rule, password migration) blocks SR-005 and the password part of SR-007. Owner: Security Officer.
- BRD Q-03 (attempt limit) blocks NFR-002. Owner: Security Officer.
- The menu slices (BRD DEP-01) must exist before sign-on can route users.

## 7. Recommended Next-Milestone Work

<!-- Ordered by priority; each item names the RTM IDs it closes and the evidence that will show it is done. -->

1. Get SME confirmation of RUL-001 to RUL-007 and decisions on Q-02 and Q-03. Closes the Candidate status of every RUL row.
2. Build user-service with SR-001 to SR-006 and DR-001, with tests for each FRD acceptance criterion. Evidence: CI run with the tests.
3. Build the SR-007 load job and reconcile against the ten seed users. Closes BR-005 and FR-010.
4. Run the FRD §14 equivalence scenarios against legacy and target.

## 8. Limitations of this Assessment

- No CardDemo tests, CI runs or deployment records were available, so nothing is Verified and legacy runtime status is Not verifiable.
- Statuses come from reading the code; every RUL is still a Candidate.
- No completion percentage: priorities are not agreed.

## 9. Open Decisions and Next Actions

| # | Decision / action | Owner | Due | RTM IDs |
|---|---|---|---|---|
| 1 | Decide the credential case rule and password migration (Q-02) | Security Officer | Unknown | BR-004, FR-008, SR-005, SR-007 |
| 2 | Decide the failed sign-on limit (Q-03) | Security Officer | Unknown | NFR-002 |
| 3 | Confirm the two roles and the role check (RUL-006) | Product Owner | Unknown | RUL-006, FR-006 |
| 4 | Decide the Exit key on Add User (Q-07) | Product Owner | Unknown | FR-009 |

