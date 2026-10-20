# Standard prompt structure

Each prompt has the same eight blocks, in this order. Blocks that don't apply say `N/A`.

```markdown
## 1. Role
Act as <roles>, e.g. senior business analyst, solution architect, quality engineer.

## 2. Context
- Project: [NAME]                      - Business owner: [NAME / TEAM / Unknown]
- Users and customers: [GROUPS]        - Stage: [Legacy in production | Migration in progress | ...]
- Source location: [PATH or REPO URL]  - Commit / tag: [SHA]
- Target stack: [e.g. React 19 + Spring Boot 3 (Java 21) + DB2 for z/OS 13 | Unknown]
- Constraints: [budget, timeline, regulatory, technology mandates | Unknown]
- Existing documents: [links | none]
(or: "See docs/requirements/PROJECT-CONTEXT.md")

## 3. Task
One sentence: what to produce or change.

## 4. Scope
- Slice: [transactions / jobs / programs / feature name]
- In scope / out of scope: [...]

## 5. Inputs
Files, documents, interview notes, upstream documents (with versions).

## 6. Deliverables
Exact documents and where they go (default docs/analysis/ and docs/requirements/).

## 7. Rules
- Follow the standard document structure. Don't remove, rename or renumber sections; use "N/A: <reason>".
- Never invent facts, decisions, numbers, approvals, test results or deployments. Write Unknown, or
  TBD (decision needed: ..., owner: ...), and add an open question.
- Label each requirement's basis: Confirmed | Derived from code (candidate) | Assumption | Proposed.
- Evidence is a hyperlink to the exact source lines (path:line, then `docver.py linkify`). Never paste source code.
- Use stable IDs (BR/FR/SR/...). Never renumber; retire instead.
- Every change to an existing document: bump the version first, add a revision row, edit, then validate.
- Don't shrink requirements to match what the code does; record the gap.

## 8. Verification and report
Run `docver.py validate` (and `--strict` before a baseline). Report the version changes, sections changed,
IDs added or retired, the validation result, and the open questions and decisions.
```

Why this shape: the context and rules blocks are what keep different people (and different runs) producing comparable,
honest documents. The scope block keeps large estates manageable. The verification block makes every run end
with a checked, versioned result instead of "done".
