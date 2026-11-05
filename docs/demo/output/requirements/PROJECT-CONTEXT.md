---
doc_type: CONTEXT
doc_id: CONTEXT-CARDDEMO
title: "CardDemo: Project Context"
project: "CardDemo"
business_owner: "Demo owner"
version: 0.1.0
status: Draft
last_updated: 2026-11-05
target_stack: "React + Spring Boot + DB2"
source_root: "../../../carddemo/app"
repo_url: "https://github.com/aws-samples/aws-mainframe-modernization-carddemo"
repo_ref: "59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e"
repo_subdir: "app"
---

# CardDemo: Project Context

<!-- Shared facts every BRD/FRD/SRD/RTM/GAP iteration starts from. Fill what is known; write "Unknown" otherwise
and add the question to the documents' Open Questions. docver.py reads the front matter:
- source_root: path from this file's folder to the source tree (used for relative evidence links)
- repo_url + repo_ref: repository web URL and the commit SHA (or tag) to pin permalinks to. Prefer a commit SHA,
  because a branch link drifts as the code changes. repo_subdir: where source_root sits inside the repository. -->

## 1. Document Control

### 1.1 Revision History

| Version | Date | Author | Change summary | Sections changed |
|---|---|---|---|---|
| 0.1.0 | 2026-11-05 | Claude (draft) | Initial context | All |

## 2. Project

| Field | Value |
|---|---|
| Product or project | CardDemo |
| Business owner | Demo owner |
| Intended users and customers | Back-office staff of a card issuer: administrators and regular users (CardDemo is an AWS sample application) |
| Product stage | Migration planned (demonstration) |
| Target stack | React + Spring Boot + DB2 |

## 3. Sources

| Field | Value |
|---|---|
| Repository or source location | https://github.com/aws-samples/aws-mainframe-modernization-carddemo |
| Commit / tag assessed | 59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e |
| Analysis knowledge base | docs/analysis/ |
| Existing documents and reference links | https://github.com/aws-samples/aws-mainframe-modernization-carddemo/blob/59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e/README.md |

## 4. Known Constraints

<!-- Budget, timeline, technology mandates, regulatory, staffing, freeze windows. -->

- Demonstration only: no real stakeholders were interviewed, so every requirement is derived from code and stays a candidate.
- Slice: sign-on (CC00) and add user (CU01). Budget, timeline and regulatory scope: Unknown.

## 5. Assessment

| Field | Value |
|---|---|
| Assessment date | 2026-11-05 |
| Branch / tag / commit | 59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e |
| Environments with deployment evidence | Unknown |
