---
name: requirements-docs
description: Generate and iterate a standard requirements package covering the Business Requirements Document (BRD), Functional Requirements Document (FRD), System Requirements Document (SRD), Requirements Traceability Matrix with implementation status (RTM), and Executive Progress and Gap Report. Each document has a fixed section structure and semantic versioning: every update bumps the version, adds a revision row and snapshots the old version. IDs are stable and traced BR → FR → SR → code/test evidence. Evidence is given as hyperlinks to the source lines (no copied code), and Mermaid/UML diagrams cover context, use case, sequence, state, ER, component and deployment views. Works from existing code (via legacy-code-analysis), notes or upstream documents, in any language. Use this whenever the user asks to write, generate, update, version, review or derive a BRD, FRD, SRD/SRS, functional or technical spec, traceability matrix, requirements coverage, implementation status, or gap analysis, even if they just say "requirements doc", "spec", or "how much of this is built".
---

# Requirements package: BRD → FRD → SRD → RTM → Gap report

| Doc | File | Answers | Defines |
|---|---|---|---|
| Project context | `PROJECT-CONTEXT.md` | Facts every document starts from: owner, users, repo + commit, constraints | — |
| BRD | `BRD.md` (21 sections) | Why, and what business outcome | BO, BR, RUL, ASM/CON/DEP, RSK |
| FRD | `FRD.md` (17 sections) | What the solution does | UC, FR, SCR, BAT, RPT, INT, MSG |
| SRD | `SRD.md` (23 sections) | How the system is built and constrained (System Requirements Document) | SR, NFR, IFR, DR, ADR |
| RTM | `RTM.md` | Each requirement's trace, code/verification/deployment status and gap | rows for BR, RUL, FR, SR, NFR, IFR, DR |
| Gap report | `GAP-REPORT.md` | Executive progress, gaps, blockers, next milestone | — |

Templates in `assets/templates/` are the standard. Section numbers and titles are fixed, and `docver.py validate` checks them
in order. A section that doesn't apply says `N/A: <reason>`. Never delete or renumber a section: that's what keeps every
version and every project comparable. Tooling: `D=<skill-dir>/scripts/docver.py` (`<skill-dir>` = this skill's folder).
Default folder: `docs/requirements/`, with `history/` for snapshots.

## Choose what to produce

Decide from the request; ask once with these options only if it's genuinely unclear:

1. **BRD only**
2. **BRD → FRD**
3. **BRD → FRD → SRD** (full specification)
4. **FRD or SRD from an existing upstream document**
5. **Implementation assessment**: RTM + Gap report against a codebase (needs at least one requirements document)
6. **Update / iterate** any document (standard iteration protocol below)
7. **Status / traceability report**: `docver.py status`, `trace`, `rtm summary`, with no content change

For a large estate, also agree the slice (domain/capability) per document set (`references/writing-guide.md` §6).

## Start: project context (once per project)

```bash
python3 $D init --type context --dir docs/requirements --project "<Name>" --owner "<owner or Unknown>" --src <source-root>
```

`--src` detects the git remote and HEAD commit, so evidence links become permalinks pinned to that commit. Without git,
links are relative paths to `source_root`. Fill the remaining fields (users, stage, constraints, existing documents). Unknown
facts stay **Unknown**, and each one becomes an open question.

## Inputs, in order of preference

1. **Source code**: if `docs/analysis/inventory.json` is missing, run `legacy-code-analysis` first (scan → slice → rules).
   Writing requirements from raw source without an inventory misses scope.
2. **Analysis knowledge base**: `inventory.md`, program cards (already linked to source lines), `rules/*.md`.
3. **User material**: notes, interviews, existing specs, regulations, tickets.
4. **Upstream documents**: BRD for the FRD; FRD + BRD for the SRD; all three for the RTM.
5. **Mainframe → React / Spring Boot / DB2**: `mainframe-modernization` supplies the SRD target design.

## Honesty rules (they apply to every document)

- **Never invent** decisions, stakeholders, numbers, SLOs, security guarantees, approvals, test results or deployment facts.
  Write **Unknown**, or `TBD (decision needed: …, owner: …)`, and add an open question.
- **Priorities are the business's call.** When none was given, write `Unknown (proposed: Must)`. `rtm sync` then records
  Unknown, which is correct until someone agrees it.
- **Label the basis** of each BR/FR/SR: `Confirmed (who/what)`, `Derived from code (candidate)`, `Assumption`, or `Proposed`.
  Keep facts, assumptions and recommendations visibly separate.
- **Rules from code are candidates** (`Validation status: Candidate`) until an SME confirms them.
- **Don't shrink scope to fit the code.** If the code doesn't do something the requirement asks for, that's a gap for the
  RTM, not a reason to rewrite the requirement.
- **Flag conflicts and duplicates** (between requirements, or between requirement and code) in Open Questions or RTM §5,
  with a recommended resolution.

## Evidence is a link, never a copy

Cite source as one `path:line` or `path:start-end` per reference (paths relative to `source_root`; repeat the path for
each reference). Then run `python3 $D linkify docs/requirements` to turn each one into a hyperlink. It is safe to re-run,
because existing links are left alone, and it also works on analysis notes (`linkify docs/analysis --context docs/requirements/PROJECT-CONTEXT.md`).
For files outside `source_root`, write the permalink by hand. It produces a repo permalink at the pinned commit
(GitHub/GitLab/Bitbucket/Azure DevOps), or a relative link to the local file. Don't paste COBOL/JCL/source into the documents.
`validate` warns on copied legacy code and on unlinked `path:line` references. Name the paragraph, method or symbol next to
the link so the reader knows what to look at. Diagrams (Mermaid) and target-side drafts (for example DDL in the SRD)
are fine as code blocks.

## Create documents (version 0.1.0)

```bash
python3 $D init --type brd --dir docs/requirements --source-baseline "inventory.json scanned <ts>, slice <roots>, commit <sha>"
python3 $D init --type frd --dir docs/requirements     # derived_from = BRD automatically
python3 $D init --type srd --dir docs/requirements     # derived_from = FRD, BRD
```

Fill every section, following the HTML comments in the template (authoring guidance, ignored by validation). Use
`references/writing-guide.md` for what goes where, and `references/diagrams.md` for the diagram each section needs.
Filling the initial skeleton is part of 0.1.0, so don't bump while drafting the first version. Write the BRD before the FRD before the SRD.

## Assess implementation (RTM + Gap report)

```bash
python3 $D init --type rtm --dir docs/requirements && python3 $D init --type gap --dir docs/requirements
python3 $D rtm sync docs/requirements        # one row per BR/RUL/FR/SR/NFR/IFR/DR; keeps existing assessments
```

Then assess each row from evidence, following `references/implementation-assessment.md` (what to inspect, status rules,
what does and doesn't count as evidence). Fill the code, verification and runtime columns separately, with links. Then:

```bash
python3 $D linkify docs/requirements && python3 $D rtm summary docs/requirements   # counts → RTM §4.1 and GAP §3-4
```

Write the Gap report narrative (§2, §5–§9) from the RTM, citing row IDs. Add `--weighted` to `rtm summary` only when
priorities are agreed; it prints its formula and exclusions. Otherwise report counts, not percentages.

## Standard iteration protocol (every request that changes a document)

Every prompt that changes content is one iteration and follows the same steps:

1. **Identify** the document(s), the change and the sections affected, including the downstream impact (a new BR needs FRs,
   SRs and RTM rows). Do the downstream changes, or list them as pending.
2. **Bump first.** This snapshots the released version to `history/<name>_v<old>.md`:
   `python3 $D bump docs/requirements/BRD.md --level minor --summary "<what and why>" --sections "10, 11"`
   `patch` = editorial only; `minor` = any content change (the default); `major` = baseline/approval
   (`--status Approved`, 0.x → 1.0.0). Pass `--author` with the requester's name when a person asked for the change.
3. **Edit** only the affected sections. IDs are permanent: new items take the next free number, and removed items stay with `Status: Retired`.
4. **Link, trace, sync, validate:**
   ```bash
   python3 $D linkify docs/requirements
   python3 $D trace docs/requirements --inject
   python3 $D rtm sync docs/requirements          # if an RTM exists
   python3 $D validate docs/requirements
   python3 $D diff docs/requirements/BRD.md       # confirm the sections changed match the revision row
   ```
   Fix every ERROR. For a Draft, explain any remaining WARNs (for example sections not yet in scope).
5. **Staleness**: when `validate` reports `STALE`, review the upstream diff, update the downstream document, and bump it with
   `--refresh-upstream`.
6. **Report**: version old → new per document, sections changed, IDs added or retired, validation result, and new open
   questions or decisions.

## Quality bar for a version

- `validate` shows no errors. Before a baseline (major), run `validate --strict` too, which also fails on empty sections,
  missing diagrams, TBDs without a decision, and unassessed RTM rows.
- Traces: BR → BO, FR → BR, SR → FR, and NFR/IFR/DR → BR/FR/RUL or "technical (reason)". Every RUL has a linked Source and a Validation status.
- Required diagrams present (BRD §7, §8, §12; FRD §2, §4, §6, §7; SRD §2, §3 ×2, §4, §7, §17), plus more wherever a flow
  is clearer drawn than written.
- No technology in the BRD, no design in the FRD, numbers (or TBD + decision) on every SRD quality target.
- Every open question and decision has an owner.

## Large packages

Work section by section and validate as you go. For big slices, delegate per domain to subagents. Give each one the template
section, the evidence files, the honesty and evidence rules above, and a reserved ID range (for example FR-200..FR-299).
Merge the results, then run linkify / trace / validate once.

## Export

Markdown renders with diagrams in GitHub/GitLab/VS Code. For Word/PDF, pre-render the Mermaid blocks
(`npx -y @mermaid-js/mermaid-cli -i BRD.md -o BRD.rendered.md`), then use pandoc or the `docx`/`pdf` skills.
