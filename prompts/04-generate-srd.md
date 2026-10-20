# Prompt: generate the SRD (System Requirements Document)

```markdown
## 1. Role
Act as a solution architect, DBA and security engineer.

## 2. Context
See docs/requirements/PROJECT-CONTEXT.md. Target stack: [React x + Spring Boot x (Java x) + DB2 for z/OS | Db2 LUW x | Unknown].

## 3. Task
Derive the System Requirements Document from FRD.md [X.Y.Z] and BRD.md [X.Y.Z], including the legacy-to-target design.

## 4. Scope
Same slice as the FRD. Migration strategy constraints: [rewrite | convert | rehost per domain | Unknown].

## 5. Inputs
FRD.md, BRD.md, docs/analysis/ (inventory, data dictionary, CRUD matrix), target-mapping.md and data-mapping.md (mapgen).

## 6. Deliverables
docs/requirements/<module>/<feature>/SRD.md (standard 23-section structure) with ADRs for every significant choice.

## 7. Rules
- Use the mainframe-modernization skill for target patterns: CICS to REST + React, JCL to Spring Batch,
  VSAM/copybooks to DB2, transactions and concurrency, waves, equivalence testing.
- Every SR traces to an FR. NFR/IFR/DR trace to BR/FR/RUL, or say "technical (reason)".
- Quality targets are numbers or TBD (decision needed: ..., owner: ...). Never invent SLOs or security guarantees.
- §18.1 covers every legacy artifact in the slice: a target, or "Retired (reason)". Link legacy artifacts, don't paste code.
- Required diagrams: context (§2), components plus sequence (§3), deployment (§4), physical ER (§7.1), batch (§17).

## 8. Verification and report
Run linkify, trace --inject and validate (--strict before a baseline). Report the FR→SR coverage, the ADRs and their status, and open decisions.
```
