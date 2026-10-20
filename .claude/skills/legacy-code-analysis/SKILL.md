---
name: legacy-code-analysis
description: Analyze an existing codebase (mainframe COBOL/CICS/JCL/BMS/DB2/VSAM/IMS, PL/I, Assembler, RPG, Natural, or Java/.NET/Python/JS) and build an evidence-backed knowledge base. It covers the program inventory, call/transfer graph, CRUD matrix, data dictionary, screens, batch flows, candidate domains, and business rules with file:line sources. Use this whenever the user wants to understand, reverse-engineer, document, assess or modernize legacy source code. Typical requests are "analyze this COBOL", "what does this mainframe app do", "extract the business rules", "inventory the codebase", "map dependencies", or a migration assessment. Run it before writing a BRD/FRD/SRD from code. It works even when the user doesn't say "analysis", for example when they hand over a folder of .cbl/.jcl files and ask about it.
license: Apache-2.0
---

# Legacy code analysis

Produce a knowledge base about an existing system that later documents (BRD, FRD, SRD) and migration
designs can cite. Every claim it makes must point to the source (`path:line`), because requirements
recovered from code are only trusted when someone can check them.

## Outputs (default `docs/analysis/`, next to the requirements docs)

| File | Made by | Contents |
|---|---|---|
| `inventory.json` | script | Everything below in machine-readable form (re-used by `slice`, `domains`, and the modernization mapping) |
| `inventory.md` | script | Counts, entry points (transactions, jobs), program table, unresolved references |
| `callgraph.mmd` | script | Mermaid graph: transaction/job → program → XCTL/LINK/CALL |
| `crud-matrix.md` | script | Program × table/file/dataset with C/R/U/D |
| `data-dictionary.md` | script | DB2 tables (DDL/DCLGEN) and copybook layouts with suggested DB2/Java types |
| `screens.md` | script | BMS maps: fields, role (input/output/label), position, length, attributes |
| `batch-flows.md` | script | One Mermaid flow per JCL job: steps, programs, datasets |
| `programs/<PGM>.md` | script | Program card: callers, callees, data, screens, paragraphs + PERFORM tree, 88-levels, messages, line evidence |
| `domains.md` | script (`domains`) | Candidate business domains (clusters of programs sharing data) |
| `system-overview.md` | you | Business-level narrative: what the system does, actors, capabilities, key flows (with diagrams) |
| `rules/<domain>.md` | you | Business rule catalogue per domain (RUL candidates with evidence) |
| `findings.md` | you | Legacy defects, anomalies and risks found while reading (F-nn, linked evidence). They feed BRD §7 pain points, §15 risks and deliberate changes in the FRD |
| `analysis-notes.md` | you | What was read, coverage, open questions, assumptions; append each session |

## Workflow

### 1. Scan (deterministic, seconds)

```bash
python3 <skill-dir>/scripts/inventory.py scan --src <source-root> --out docs/analysis
python3 <skill-dir>/scripts/inventory.py domains --inventory docs/analysis/inventory.json
```

`<skill-dir>` is this skill's folder. The scanner classifies files by extension *and* content (mainframe
exports often have no or wrong extensions), handles fixed-format COBOL columns, resolves dynamic
`XCTL/LINK/CALL` targets from `MOVE`/`VALUE` literals, finds DB2 batch programs behind
`IKJEFT01 … RUN PROGRAM(x)`, and never stops on an odd file (errors are recorded per file).
Read `inventory.md` first. It tells you the shape of the system in one page.

### 2. Close the gaps the scanner reports

`inventory.md` → *Unresolved references* lists missing copybooks/programs, unresolved dynamic calls
and missing PROCs. For each one, either find the source (ask the user for the missing members), resolve it
by reading the code (for example a table-driven menu: read the option table copybook), or record it as an
open question. Don't silently drop them: a missing program is missing scope.

### 3. Pick the slice

Large systems are analyzed by business capability, not all at once. Use `domains.md` and the entry points to
propose slices (for example "Sign-on and user admin: CC00, CU00-CU03"), name them in business terms, and
agree the order with the user when the scope is unclear. Then list exactly what to read:

```bash
python3 <skill-dir>/scripts/inventory.py slice --inventory docs/analysis/inventory.json --root CC00 CU00 CU01 CU02 CU03 --depth 2
```

`--root` takes one or more transaction IDs, job names or program names. It returns the programs (it doesn't expand
through menus/dispatchers unless they are roots), copybooks, tables, CICS files, datasets, transactions, the jobs that run
the slice's programs or define/load its datasets, the CSD, and the exact `files_to_read`.

### 4. Read and extract (the judgement part)

For each program in the slice, start from its card, then read the source. Extract:
- **Purpose** in one business sentence (header comments + paragraph names + screens/data used).
- **Business rules** following `references/business-rule-extraction.md` (validation, calculation, decision,
  state transition, constraint, authorization), each with `path:line`, type, confidence and
  `Validation status: Candidate`.
- **Flows**: the online dialogue (screen → key → program → next screen) and batch chains (job → steps → files).
- **Messages** (from the card) as validation rules and the message catalogue.
- **Data meaning**: what each entity/field means to the business (data dictionary + usage).

Use `references/mainframe-constructs.md` whenever a construct's business meaning is unclear (pseudo-conversational
CICS, COMMAREA, GDGs, COND codes, PIC/COMP-3, REDEFINES, DL/I calls). For many programs, fan out one
subagent per program or domain with the program card plus files to read. Have each one return rules and flows
in the formats above, then merge and deduplicate them.

### 5. Write the narrative and diagrams

`system-overview.md` should give a reader the system in ten minutes: context diagram (actors, system, external
parties, data stores), capability list mapped to transactions/jobs, a main online flow (Mermaid `sequenceDiagram`
or `stateDiagram-v2` of screen navigation), the batch cycle (Mermaid flowchart), and a conceptual
`erDiagram`. Use business names and put program names in parentheses or notes.

### 6. Log

Record legacy defects and anomalies (security gaps, unchecked inputs, wrong messages, dead keys, lost updates,
contradictions) in `findings.md` as F-nn with linked evidence. They're often the most valuable output for the business.
Each one later becomes a pain point, a risk, or a "Deliberate change" in the FRD.

Append to `analysis-notes.md`: date, slice, files read, rules found (IDs), coverage table, open questions,
and the `inventory.json` scan timestamp. The next session or a subagent continues from here instead of re-reading.

## Principles

- **Evidence or it didn't happen, and evidence is a link.** Every rule, flow and data claim cites the source lines as a
  hyperlink (or "SME: name, date"). The scanner records the git remote and commit (or use `--repo-url/--repo-ref`), and
  its reports and program cards already link to exact lines. In your own notes write one `path:line` or
  `path:start-end` per reference (repeat the path for each: `cbl/A.cbl:120, cbl/A.cbl:125`). Then run
  `docver.py linkify docs/analysis --context docs/requirements/PROJECT-CONTEXT.md` to convert them; it is safe to re-run.
  For a file outside the scanned source root (for example a repo README), write the permalink by hand. Don't paste source code into the knowledge base or documents. Unverifiable statements go to Open Questions.
- **Candidates, not facts.** Code shows what the system does, not what the business wants. Some behaviour is a
  bug or a workaround. The SME confirms. Say this plainly in what you write.
- **Business language up, code names down.** Rules and narratives are in business terms; identifiers live in
  the evidence.
- **Language-agnostic.** The same steps apply to any stack: the scanner gives a generic inventory (imports,
  units, endpoints, SQL tables) for non-mainframe languages. Then read controllers/handlers for behaviour,
  services for rules, and entities/repositories for data.
- **Re-run the scan whenever source changes** and record the new timestamp. Documents cite the scan they were
  based on (`source_baseline`).

## Next steps

Hand the knowledge base to the `requirements-docs` skill (BRD → FRD → SRD), and for a mainframe migration to
`mainframe-modernization` for target mapping.
