# Prompt templates

Every request to the skills uses the same **standard prompt structure**, so each run (and each document version it
produces) can be repeated and audited. Copy a template, fill the `[BRACKETS]`, and paste it into Claude Code
in the project folder.

| Template | Use it to | Skills it drives |
|---|---|---|
| [`00-standard-prompt-structure.md`](00-standard-prompt-structure.md) | Understand and write your own prompts in the standard shape | all |
| [`01-analyze-legacy-code.md`](01-analyze-legacy-code.md) | Build the analysis knowledge base for a slice of the code | legacy-code-analysis |
| [`02-generate-brd.md`](02-generate-brd.md) | Write the Business Requirements Document | requirements-docs |
| [`03-generate-frd.md`](03-generate-frd.md) | Derive the Functional Requirements Document from the BRD | requirements-docs |
| [`04-generate-srd.md`](04-generate-srd.md) | Derive the System Requirements Document with the target design | requirements-docs, mainframe-modernization |
| [`05-change-request.md`](05-change-request.md) | Change a document and carry it downstream (version bump) | requirements-docs |
| [`06-implementation-assessment.md`](06-implementation-assessment.md) | Build the RTM and Executive Gap Report against a codebase | requirements-docs |
| [`master-prompt-full-package.md`](master-prompt-full-package.md) | One prompt for the whole package: BRD, FRD, SRD, RTM, gap report | all |

Tips:
- Fill `docs/requirements/PROJECT-CONTEXT.md` once (owner, users, repo, commit, constraints). Then the context block in each
  prompt can just say "see PROJECT-CONTEXT.md".
- Leave a field as `Unknown` rather than guessing. The skills turn unknowns into open questions instead of inventing answers.
- Name the slice (transactions, jobs, programs, or a feature) for anything larger than a few dozen programs.
