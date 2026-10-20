---
doc_type: BRD
doc_id: {{DOC_ID}}
title: "{{PROJECT}}: Business Requirements Document"
project: "{{PROJECT}}"
owner: "{{OWNER}}"
version: 0.1.0
status: Draft
last_updated: {{DATE}}
authors: ["{{AUTHOR}}"]
derived_from: []
source_baseline: "{{SOURCE_BASELINE}}"
target_stack: "{{TARGET_STACK}}"
---

# {{PROJECT}}: Business Requirements Document (BRD)

<!-- Structure basis: IIBA BABOK v3 business-requirement concepts plus the common BRD section set.
Section numbers and titles are fixed; docver.py validates them in order. Write "N/A: <reason>" in a section
that does not apply instead of deleting it. Label unknown information "Unknown" (or TBD + the decision needed)
and add it to section 19. Never invent decisions, numbers or approvals.
IDs: BO-nn objective, BR-nnn business requirement, RUL-nnn business rule, ASM/CON/DEP-nn, RSK-nn.
IDs are permanent: never renumber; retire with "Status: Retired". -->

## 1. Document Control

### 1.1 Document Information

| Field | Value |
|---|---|
| Purpose | Defines the business need, outcomes and requirements for {{PROJECT}} |
| Owner | {{OWNER}} |
| Version / date | see front matter and 1.2 |
| Approval status | Draft |
| Project context | PROJECT-CONTEXT.md |

### 1.2 Revision History

<!-- Maintained by docver.py bump. One row per version; newest last. -->

| Version | Date | Author | Change summary | Sections changed |
|---|---|---|---|---|
| 0.1.0 | {{DATE}} | {{AUTHOR}} | Initial draft | All |

### 1.3 Approvals

| Role | Name | Decision | Date |
|---|---|---|---|
| Business Sponsor | Unknown | Pending | |
| Product Owner | Unknown | Pending | |
| Business SME | Unknown | Pending | |

### 1.4 Source Baseline

<!-- What this version is based on: inventory scan time, source root, branch/commit, slice, documents, interviews. -->

## 2. Executive Summary

<!-- 5-10 sentences for an executive who reads nothing else: what the system does for the business, why change now,
the change, headline scope, expected outcomes. Write it last. -->

## 3. Business Context and Problem or Opportunity

### 3.1 Current Situation
### 3.2 Business Drivers
### 3.3 Problem or Opportunity Statement

## 4. Product Vision and Desired Business Outcomes

## 5. Objectives and Success Metrics

<!-- SMART objectives with KPI, baseline and target. Unknown baseline/target: "TBD (decision: ..., owner: ...)". -->

| ID | Objective | KPI | Baseline | Target | Owner |
|---|---|---|---|---|---|

## 6. Stakeholders, User Groups and Decision Owners

### 6.1 Stakeholder Register

| Stakeholder / Role | Interest | Influence | Responsibility (RACI) | Decision owner for |
|---|---|---|---|---|

### 6.2 User Groups and Personas

<!-- For legacy systems: derive from security profiles, sign-on user types and menu options (cite evidence). -->

## 7. Current-State Process and Pain Points

<!-- Business view of today's processes. Mermaid flowchart per major process (online and batch) required.
Pain points as a list with evidence (incident data, stakeholder statements, code findings). -->

## 8. Target-State Business Process

<!-- Same processes after the change; mark what changes (new, removed, automated). Mermaid diagram required. -->

## 9. Scope

### 9.1 In Scope
### 9.2 Out of Scope
### 9.3 Future Considerations

## 10. Business Requirements

<!-- One block per requirement. Business-level non-functional needs (batch deadlines, volumes, availability windows)
are BRs too, with Category: Non-functional. Template:

### BR-001: <short name>
- **Statement:** The business needs ... so that ...
- **Category:** Functional | Non-functional | Data | Reporting | Compliance | Transition
- **Rationale:**
- **Supports:** BO-01
- **Priority:** Must | Should | Could | Won't (MoSCoW) | Unknown
- **Basis:** Confirmed (<who/what>) | Derived from code (candidate) | Assumption | Proposed
- **Source:** stakeholder / document / legacy evidence `path:line`
- **Acceptance criteria:** measurable condition(s)
- **Status:** Proposed | Confirmed | Retired
-->

## 11. Business Rules and Policy Constraints

<!-- Rules recovered from code are CANDIDATES until a business SME confirms them. Template:

### RUL-001: <short name>
- **Rule:** plain-language rule (no program or variable names here)
- **Type:** Validation | Calculation | Decision | State transition | Constraint | Authorization | Policy
- **Source:** `cbl/PROGRAM.cbl:120-131` (paragraph NAME) or policy document
- **Validation status:** Candidate | SME-confirmed | Rejected
- **Confidence:** High | Medium | Low (reason: e.g. single explicit IF / inferred / dynamic dispatch)
- **Applies to:** BR-00x
-->

## 12. Business Data and Reporting

### 12.1 Business Entities
### 12.2 Conceptual Data Model
<!-- Mermaid erDiagram, business names only. -->
### 12.3 Reports, Statements and Business Outputs

## 13. Expected Benefits and Measurement

| Benefit | Measure | Baseline | Target | When measured | Owner |
|---|---|---|---|---|---|

## 14. Assumptions, Dependencies and Constraints

| ID | Type | Description | Impact if wrong |
|---|---|---|---|

## 15. Business Risks and Mitigations

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|

## 16. Compliance, Privacy and Records Retention

<!-- Regulations, personal/sensitive data, retention periods, audit obligations. "N/A: <reason>" if none apply. -->

## 17. Transition and Migration Requirements

<!-- Modernization: functional-equivalence expectations, data migration, parallel run, cutover window, coexistence,
decommissioning, training. "N/A: greenfield" otherwise. -->

## 18. Acceptance and Approval Criteria

## 19. Open Questions and Decisions Needed

| # | Question / decision | Owner | Due | Answer / decision |
|---|---|---|---|---|

## 20. Glossary

| Term | Definition |
|---|---|

## 21. Appendices

### 21.1 Traceability Summary

<!-- trace:begin -->
<!-- trace:end -->

### 21.2 Source Evidence Index
