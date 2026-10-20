---
description: Build the RTM and Executive Gap Report for a feature against the current codebase
agent: agent
argument-hint: feature=<module/feature> commit=<sha>
---

Use the `requirements-docs` skill and its `references/implementation-assessment.md`.
Follow [prompts/06-implementation-assessment.md](../../prompts/06-implementation-assessment.md).

- Feature folder: docs/requirements/${input:feature:module/feature}/
- Commit assessed: ${input:commit:commit SHA (set repo_ref in PROJECT-CONTEXT.md to it)}

Run `docver.py init --type rtm --dir <folder>`, `init --type gap --dir <folder>` and `rtm sync <folder>`. Assess every row from evidence:
code, verification and deployment status separately, linked evidence, gap, next action and confidence. Mocks, TODOs, flags and UI-only
elements don't count, and nothing is Deployed without release evidence. Then run `linkify`, `rtm summary`, write the gap-report narrative,
`validate` and `index docs/requirements`. No completion percentage unless priorities are agreed.
