# Prompt: implementation assessment (RTM + Executive Gap Report)

```markdown
## 1. Role
Act as a senior business analyst, software architect and quality engineer.

## 2. Context
See docs/requirements/PROJECT-CONTEXT.md. Assessment date: [DATE]; repository: [URL]; branch/tag/commit: [SHA].

## 3. Task
Assess how much of the requirements in BRD/FRD/SRD [versions] are implemented, verified and deployed in the codebase at [SHA].

## 4. Scope
All requirements in the documents (BR, RUL, FR, SR, NFR, IFR, DR), unless stated: [...]

## 5. Inputs
Source code, configuration, schema and migrations, API definitions, UI, tests and results, CI/CD workflows and runs,
deployment configuration and release notes. Artifacts I can't give you access to: [LIST or none].

## 6. Deliverables
docs/requirements/<module>/<feature>/RTM.md (one row per requirement) and GAP-REPORT.md in the same folder.

## 7. Rules
- Code status (Implemented / Partially / Not implemented / Blocked / Not applicable / Not verifiable), verification status
  and runtime/deployment status are separate judgements, each with linked evidence.
- Mocks, stubs, TODOs, disabled flags, UI-only elements and untested paths are not proof of a working capability.
- No "Deployed" without deployment evidence. Anything you can't inspect is Not verifiable, and you say why.
- Don't change requirements to match the code; record conflicts and duplicates with a recommended resolution.
- No completion percentage unless priorities are agreed; if you show one, state the formula and exclusions.

## 8. Verification and report
Run rtm sync, linkify, rtm summary and validate. The gap report gives the scope and evidence, counts by document and status,
implemented-but-not-verified items, the highest-impact gaps, blockers, next-milestone work by priority, limitations, and open decisions.
```
