---
doc_type: FRD
doc_id: {{DOC_ID}}
title: "{{PROJECT}}: Functional Requirements Document"
project: "{{PROJECT}}"
owner: "{{OWNER}}"
version: 0.1.0
status: Draft
last_updated: {{DATE}}
authors: ["{{AUTHOR}}"]
derived_from: {{DERIVED_FROM}}
source_baseline: "{{SOURCE_BASELINE}}"
target_stack: "{{TARGET_STACK}}"
---

# {{PROJECT}}: Functional Requirements Document (FRD)

<!-- WHAT the solution must do: behaviour visible to users and other systems, independent of how it is built.
Every FR traces to at least one BR in the upstream BRD (derived_from).
IDs: UC-nn use case, FR-nnn functional requirement, SCR-nn screen, BAT-nn batch function, RPT-nn report,
INT-nn interface, MSG-nnn message. "N/A: <reason>" for sections that do not apply; "Unknown" for missing facts. -->

## 1. Document Control

### 1.1 Document Information

| Field | Value |
|---|---|
| Purpose | Specifies the functional behaviour of {{PROJECT}} |
| Owner | {{OWNER}} |
| Version / date | see front matter and 1.2 |
| Approval status | Draft |
| Upstream documents | see 1.4 |

### 1.2 Revision History

| Version | Date | Author | Change summary | Sections changed |
|---|---|---|---|---|
| 0.1.0 | {{DATE}} | {{AUTHOR}} | Initial draft | All |

### 1.3 Approvals

| Role | Name | Decision | Date |
|---|---|---|---|
| Product Owner | Unknown | Pending | |
| Business Analyst Lead | Unknown | Pending | |
| QA Lead | Unknown | Pending | |

### 1.4 Upstream Documents

## 2. Product Overview and Scope

<!-- Purpose, scope, definitions. Required: system context diagram (Mermaid flowchart). -->

## 3. User Roles, Actors and Permissions

| Actor / Role | Description | Legacy equivalent | Permissions |
|---|---|---|---|

## 4. User Journeys and Use Cases

<!-- Required: use-case overview diagram (Mermaid flowchart with actor nodes). Then journeys, then UC blocks:

### UC-01: <name>
- **Actor(s):**  **Traces to:** BR-00x
- **Preconditions:**  **Trigger:**
- **Main flow:** 1. ... 2. ...
- **Alternate and error flows:** 2a. ...
- **Postconditions:**
Add a Mermaid sequenceDiagram for non-trivial use cases. -->

## 5. Functional Requirements

<!-- Group by capability (### Capability, then #### FR blocks). Every FR has every field below:

#### FR-001: <short name>
- **Description:** The system shall ...
- **Traces to:** BR-001, RUL-003
- **Priority:** Must | Should | Could | Won't | Unknown
- **Actor:**
- **Preconditions:**
- **Main flow:** 1. ...
- **Alternate and error flows:** 1a. ...
- **Business rules:** RUL-...
- **Acceptance criteria:**
  - Given ... When ... Then ...
- **Basis:** Confirmed | Derived from code (candidate) | Assumption | Proposed
- **Legacy reference:** `cbl/PROGRAM.cbl` paragraph NAME (behaviour to preserve, or "Deliberate change: ...")
-->

## 6. Data Inputs, Outputs, Validation and States

### 6.1 Logical Data Model
<!-- Required: Mermaid erDiagram. -->
### 6.2 Inputs, Outputs and Validation Rules
### 6.3 User-Visible States
<!-- Lifecycle of key entities (Mermaid stateDiagram-v2). -->
### 6.4 CRUD Matrix (function × entity)

## 7. User Interface and Accessibility Requirements

<!-- One SCR-nn block per screen: purpose, navigation in/out, fields table
(name | label | type | length | required | validation | legacy field), actions (legacy PF key -> control), messages.
Required: navigation diagram (Mermaid stateDiagram-v2 or flowchart). Accessibility: target standard (e.g. WCAG 2.2 AA),
keyboard operation, screen-reader labels, focus order. -->

## 8. Search, Reporting, Notifications and Exports

## 9. Batch and Scheduled Processing

<!-- BAT-nn blocks: purpose, schedule/trigger, inputs, processing steps, outputs, restart/rerun, dependencies.
Mermaid flowchart per job chain. -->

## 10. Integrations and External System Behavior

<!-- INT-nn blocks: partner, direction, trigger, content, frequency, error handling, behaviour when the partner is down. -->

## 11. Authentication, Authorization and Audit Behavior

<!-- Role × function matrix; sign-on, session, lockout behaviour as users see it; what is audited and who can see it. -->

## 12. Error Handling and Recovery

| ID | Condition | Message text | Severity | User recovery | Legacy source |
|---|---|---|---|---|---|

## 13. Functional Dependencies and Assumptions

## 14. Acceptance and Verification Criteria

<!-- How each FR group is verified; for migrations, functional-equivalence scenarios (same inputs -> same outputs),
deliberate behaviour changes, and the comparison method. -->

## 15. Open Questions and Decisions Needed

| # | Question / decision | Owner | Due | Answer / decision |
|---|---|---|---|---|

## 16. Glossary

| Term | Definition |
|---|---|

## 17. Appendices

### 17.1 Traceability Matrix

<!-- trace:begin -->
<!-- trace:end -->
