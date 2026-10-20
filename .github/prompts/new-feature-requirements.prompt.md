---
description: Create the BRD, FRD and SRD for one feature in the standard per-feature layout
agent: agent
argument-hint: module=<kebab> feature=<kebab> [component=<kebab>] scope=<transactions/jobs/programs or description>
---

Use the `requirements-docs` skill (and `legacy-code-analysis` / `mainframe-modernization` where the scope is legacy code).
Follow the standard prompt structure in [prompts/00-standard-prompt-structure.md](../../prompts/00-standard-prompt-structure.md).

## 1. Role
Senior business analyst and solution architect.

## 2. Context
[docs/requirements/PROJECT-CONTEXT.md](../../docs/requirements/PROJECT-CONTEXT.md). If it's missing, create it first with
`docver.py init --type context --dir docs/requirements --src <source-root>` and fill in what is known; everything else is Unknown.

## 3. Task
Write the requirements for module **${input:module:module slug, e.g. accounts}**, feature **${input:feature:feature slug, e.g. account-update}**
(component: ${input:component:optional component slug}).

## 4. Scope
${input:scope:what the feature covers: legacy transactions/jobs/programs, or a description}

## 5. Inputs
The analysis knowledge base in docs/analysis/ (run the legacy-code-analysis scan and slice first if it's missing),
plus any notes or documents in the context.

## 6. Deliverables
`python3 .claude/skills/requirements-docs/scripts/docver.py new-feature --module ${input:module} --feature ${input:feature}`
creates docs/requirements/<module>/<feature>/BRD.md, FRD.md and SRD.md. Fill all three, BRD first.

## 7. Rules
As in [.github/copilot-instructions.md](../copilot-instructions.md): standard sections, no invented facts, Basis on every requirement,
evidence as links (never pasted code), stable IDs, required Mermaid diagrams.

## 8. Verification and report
Run `docver.py linkify`, `trace --inject`, `validate` on the feature folder, then `docver.py index docs/requirements`.
Report the IDs created, the validation result and the open questions with owners.
