# Master prompt: BRD, FRD, SRD and current-implementation assessment

One prompt that drives the whole package. The skills supply the structure, versioning, traceability, links and
checks; this prompt supplies the project facts and the bar.

```markdown
## 1. Role
Act as a senior business analyst, product manager, software architect and quality engineer. Create a consistent
requirements package for [PRODUCT / PROJECT NAME] and assess how much of it the current codebase implements.

## 2. Context
- Product or project: [NAME]
- Business owner: [NAME / TEAM]
- Intended users and customers: [USER GROUPS]
- Repository or source location: [REPOSITORY / WORKSPACE]
- Product stage: [In progress | Legacy in production | Migration planned]
- Existing documents or reference links: [LINKS / FILES]
- Known constraints: [BUDGET, TIMELINE, TECHNOLOGY, REGULATORY, OTHER]
- Assessment date and release/commit: [DATE, BRANCH, TAG OR COMMIT]
- Target stack (for a migration): [e.g. React + Spring Boot + DB2]

If information is missing, label it Unknown or list it as an open question. Don't invent decisions, requirements,
implementation evidence or test results. Keep confirmed facts, assumptions and recommendations clearly separate.

## 3. Task
Produce, in order: (1) BRD, (2) FRD, (3) SRD, (4) Requirements Traceability Matrix with implementation status,
(5) Executive Progress and Gap Report.

## 4. Scope
[Whole product | slice: transactions / jobs / features]. In scope / out of scope: [...]

## 5. Inputs
Review the available requirements, product documentation, source code, configuration, database schema and
migrations, API definitions, UI, tests, CI/CD workflows and deployment configuration. For every implementation claim,
give the evidence as a link (file path and lines, symbol, endpoint, migration, test, workflow or commit). If you can't
access an artifact, say what you couldn't inspect and mark the affected assessment Not verifiable.

## 6. Deliverables
docs/requirements/PROJECT-CONTEXT.md once per repository; per feature docs/requirements/<module>/<feature>/{BRD,FRD,SRD,RTM,GAP-REPORT}.md (docver.py new-feature), using the standard templates; docs/requirements/INDEX.md regenerated with docver.py index.
- BRD: purpose, owner, version, approval; executive summary; context and problem; vision and outcomes; objectives and
  metrics; stakeholders and decision owners; current process and pain points; target process; scope; business requirements
  (BR-001…); business rules and policy constraints; benefits and measurement; assumptions, dependencies, constraints;
  risks; compliance, privacy, retention; acceptance criteria; open questions.
- FRD: overview and scope; roles and permissions; journeys and use cases; functional requirements (FR-001…), each with
  description, priority, actor, preconditions, main/alternate/error flows, business rules, acceptance criteria and its BR
  links; data, validation and states; UI and accessibility; search, reporting, notifications, exports; integrations;
  authentication, authorization, audit; error handling and recovery; dependencies; verification criteria; open questions.
- SRD (System Requirements Document): scope and context; architecture and components; runtime, hosting, environments,
  deployment; interfaces, APIs, events; data, storage, lifecycle, migration, backup, retention; identity, security, secrets;
  privacy; performance and capacity; availability and recovery; logging, metrics, tracing, alerting, audit; compatibility,
  accessibility, platforms; operations; CI/CD, release, rollback; compliance; constraints; verification; open questions.
  SR-001… IDs; unknown targets are TBD with the decision needed. No invented SLOs or security guarantees.
- RTM: a row per BRD/FRD/SRD requirement with: ID and source, summary, priority, related requirements, code status,
  code evidence, verification status, verification evidence, runtime/deployment status, gap, next action, confidence.
- Gap report: scope, date, commit and evidence; counts by document and status; implemented-but-not-verified; highest-impact
  gaps and risks; blocking dependencies and decisions; next-milestone work by priority; limitations.

## 7. Rules
- Status rules: Implemented = code evidence covers the requirement (not proof of testing or deployment). Partially
  implemented = some behaviour exists, at least one acceptance criterion or flow missing. Not implemented = nothing found after
  inspecting the available source. Blocked = depends on a named unresolved dependency or decision. Not verifiable = not enough
  evidence. Track verification and deployment separately from code status. Mocks, placeholders, TODOs and disabled code are
  incomplete unless evidence shows otherwise.
- No completion percentage unless priorities or weights are agreed; if you calculate one, explain the formula and exclusions.
- Unique, stable IDs used consistently in every deliverable; specific, testable, unambiguous requirements.
- Trace BR → FR → SR → implementation evidence → verification. Identify conflicting or duplicated requirements and recommend resolutions.
- Don't silently change the requested scope to match what the code does.
- Evidence is a hyperlink to the exact lines; never paste source code into the documents.
- Every later change bumps the affected document's version, adds a revision row and snapshots the previous version.

## 8. Verification and report
Run docver.py linkify, trace --inject, rtm sync, rtm summary and validate. End with the open decisions and the
highest-priority next actions.
```
