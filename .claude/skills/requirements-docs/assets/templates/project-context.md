---
doc_type: CONTEXT
doc_id: {{DOC_ID}}
title: "{{PROJECT}}: Project Context"
project: "{{PROJECT}}"
business_owner: "{{OWNER}}"
version: 0.1.0
status: Draft
last_updated: {{DATE}}
target_stack: "{{TARGET_STACK}}"
source_root: "{{SOURCE_ROOT}}"
repo_url: "{{REPO_URL}}"
repo_ref: "{{REPO_REF}}"
repo_subdir: "{{REPO_SUBDIR}}"
---

# {{PROJECT}}: Project Context

<!-- Shared facts every BRD/FRD/SRD/RTM/GAP iteration starts from. Fill what is known; write "Unknown" otherwise
and add the question to the documents' Open Questions. docver.py reads the front matter:
- source_root: path from this file's folder to the source tree (used for relative evidence links)
- repo_url + repo_ref: repository web URL and the commit SHA (or tag) to pin permalinks to. Prefer a commit SHA,
  because a branch link drifts as the code changes. repo_subdir: where source_root sits inside the repository. -->

## 1. Document Control

### 1.1 Revision History

| Version | Date | Author | Change summary | Sections changed |
|---|---|---|---|---|
| 0.1.0 | {{DATE}} | {{AUTHOR}} | Initial context | All |

## 2. Project

| Field | Value |
|---|---|
| Product or project | {{PROJECT}} |
| Business owner | {{OWNER}} |
| Intended users and customers | Unknown |
| Product stage | Unknown (e.g. In progress, Legacy in production, Migration planned) |
| Target stack | {{TARGET_STACK}} |

## 3. Sources

| Field | Value |
|---|---|
| Repository or source location | {{REPO_URL}} |
| Commit / tag assessed | {{REPO_REF}} |
| Analysis knowledge base | docs/analysis/ |
| Existing documents and reference links | Unknown |

## 4. Known Constraints

<!-- Budget, timeline, technology mandates, regulatory, staffing, freeze windows. -->

## 5. Assessment

| Field | Value |
|---|---|
| Assessment date | {{DATE}} |
| Branch / tag / commit | {{REPO_REF}} |
| Environments with deployment evidence | Unknown |
