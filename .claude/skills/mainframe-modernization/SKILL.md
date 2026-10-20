---
name: mainframe-modernization
description: Plan and specify the migration of a mainframe application (COBOL, CICS/BMS, JCL batch, VSAM, IMS, DB2) to React + Spring Boot (Java) + DB2. It maps every legacy artifact to a target component (transaction → route/page, BMS map → React form, CICS program → REST endpoint + service, JCL job → Spring Batch job, copybook/VSAM → DB2 table + JPA entity). It also covers pseudo-conversational state, COMMAREA, SYNCPOINT, COMP-3, EBCDIC, GDGs, checkpoint/restart, coexistence waves, data migration and functional-equivalence testing. Use this whenever the user talks about mainframe modernization, COBOL to Java, CICS to REST/React, JCL to Spring Batch, VSAM or IMS to DB2, a target architecture or migration plan for legacy code, or writing the SRD/technical design of a migration, even if they only say "migrate this mainframe app".
---

# Mainframe → React + Spring Boot + DB2

This skill turns an analyzed legacy system into a target design and migration plan. It feeds the SRD (`requirements-docs`)
and design reviews. It doesn't replace requirements work: what the system must do comes from the BRD/FRD. This skill
decides how the new stack does it, and how to get there safely.

**BRD-only requests:** a BRD carries no technology, so this skill isn't needed for it. At most, run `mapgen.py` to
add the draft mapping to the knowledge base for later. Use the skill fully for the SRD, design reviews and migration planning.

## Prerequisites

- `docs/analysis/inventory.json` from `legacy-code-analysis` (scan the source first if it's missing).
- Ideally the BRD and FRD (or at least the slice's business rules), so mapping decisions trace to requirements.
- Target versions from the user or `PROJECT-CONTEXT.md` (React, Spring Boot, Java, DB2 edition/version, hosting).
  If they're unknown, record "Unknown" and an open question; don't pick versions silently.

## Workflow

1. **Generate the mapping draft** (deterministic, seconds):
   ```bash
   python3 <skill-dir>/scripts/mapgen.py --inventory docs/analysis/inventory.json            # whole estate
   python3 <skill-dir>/scripts/mapgen.py --inventory docs/analysis/inventory.json --programs COSGN00C COMEN01C   # a slice
   ```
   Writes `docs/analysis/target-mapping.md` (online → React/REST, batch → Spring Batch, data stores → DB2) and
   `data-mapping.md` (copybook fields → columns/types/Java fields, draft DDL, with links to each source file).
   The names are heuristics (screen titles, data resources). Rename them to business terms.

2. **Decide the big choices first, as ADRs** (SRD §21), each with context, options, decision and consequences:
   DB2 for z/OS vs Db2 LUW (`references/data-vsam-db2.md`), rewrite vs convert vs rehost per domain, service granularity,
   UI state strategy, batch orchestration, identity provider, coexistence approach (`references/migration-and-testing.md`).

3. **Design per domain**, using the reference that matches the artifact:
   - Online CICS/BMS → `references/online-cics-to-react-rest.md` (pseudo-conversation state machine → REST operations,
     screen → page/form, PF keys, optimistic locking, keyset paging, errors, security).
   - Batch JCL → `references/batch-jcl-to-spring-batch.md` (steps → chunk/tasklet, COND/RC → flow, GDG, restart,
     business date, SORT control cards).
   - Data → `references/data-vsam-db2.md` (PIC → types, REDEFINES/OCCURS, dates, EBCDIC, transactions, migration).
   - Waves, coexistence, testing, cutover → `references/migration-and-testing.md`.

4. **Write it into the SRD** through `requirements-docs` (bump first, then edit). Where it goes:

   | Output | SRD section |
   |---|---|
   | Context, components, sequence diagrams | §2, §3 |
   | Runtime versions, environments, deployment diagram | §4 |
   | SR-nnn per service/page/job (each traces to FR-nnn) | §5 |
   | REST endpoints, files, MQ contracts (IFR-nnn) | §6 |
   | Physical model, field mapping, migration and reconciliation (DR-nnn) | §7 |
   | Security mapping (RACF/user types → roles, IdP) | §8 |
   | Batch design, transactions, concurrency | §17 |
   | Legacy → target mapping table, waves, cutover | §18 |
   | Equivalence testing, parallel run | §20 |
   | Decisions | §21 |

   The §18.1 table must cover every legacy artifact in scope: each program, map, job, file/table and copybook gets a row
   with a target or an explicit "Retired (reason)". Link the legacy artifact to its source (`docver.py linkify`) instead of
   pasting code.

5. **Check coverage**: compare the §18.1 rows with `inventory.json` for the slice (`inventory.py slice`). Anything missing is
   unplanned scope. Unresolved references in `inventory.md` are open questions until they're closed.

## Principles

- **Requirements first, mapping second.** A legacy construct is replaced only to satisfy an FR/SR. Behaviour no requirement
  needs is a retirement candidate, recorded explicitly, never silently dropped.
- **Same results unless the BRD says otherwise.** Calculations, rounding, sort order and date handling are where migrations
  fail. Design for equivalence testing from the start, with rule-level tests and golden-master comparisons.
- **Stateless online, restartable batch, explicit units of work.** These three replace most CICS/JCL mechanics.
- **Defaults are defaults.** The mapping tables are recommendations. Record deviations as ADRs with the reason.
- **Evidence by link.** Point to legacy code with links to the exact lines. Don't copy code into design documents.
