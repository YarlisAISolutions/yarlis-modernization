# Writing guide: BRD, FRD, SRD

## Contents
1. What belongs in which document
2. IDs, traceability and basis
3. Requirement quality
4. From legacy evidence to requirements
5. Section-by-section notes
6. Sizing and slicing

## 1. What belongs in which document

| | BRD | FRD | SRD |
|---|---|---|---|
| Question | **Why** and **what outcome** | **What** the solution does | **How** it is built and constrained |
| Reader | Sponsor, business owners, SMEs | Product owner, BAs, testers, UX | Architects, developers, DBAs, ops, security |
| Language | Business terms only | User/system behaviour, screens, data, batch | Components, APIs, schemas, quality targets |
| Legacy names | Only inside evidence links | In "Legacy reference" lines | Freely (mapping tables) |
| Example | "Cardholders' balances must reflect the day's transactions before 06:00." | "FR-031: The system shall post each valid daily transaction to its account and reject invalid ones with a reason code." | "SR-087: The posting job shall commit per chunk of 500 and be restartable from the last committed chunk." |

A sentence that names a technology doesn't belong in the BRD. A sentence with no observable behaviour doesn't belong
in the FRD. A sentence without a number or testable condition isn't an SRD requirement yet. Without the number, write
`TBD (decision needed: …, owner: …)`.

## 2. IDs, traceability and basis

| Doc | Defines | Must reference |
|---|---|---|
| BRD | BO-nn, BR-nnn, RUL-nnn, ASM/CON/DEP-nn, RSK-nn | BR → BO |
| FRD | UC-nn, FR-nnn, SCR-nn, BAT-nn, RPT-nn, INT-nn, MSG-nnn | FR → BR (+ RUL applied); UC → BR or FR |
| SRD | SR-nnn, NFR-nnn, IFR-nnn, DR-nnn, ADR-nn | SR → FR; NFR/IFR/DR → BR/FR/RUL or "Traces to: technical (reason)" |

- Define an ID once, as a heading (`#### FR-012: Post daily transactions`) or as the first cell of a table row.
- IDs are permanent. Never renumber. A removed item keeps its ID with `Status: Retired`, so links, tests and RTM rows stay valid.
- New items take the next free number, even when inserted mid-section.
- **Basis** on every BR/FR/SR/NFR: `Confirmed (source)`, `Derived from code (candidate)`, `Assumption`, `Proposed`.
  This separates facts from assumptions and recommendations without extra prose.
- `docver.py validate` checks definitions, duplicates, dangling references, traces and basis. `trace --inject` writes the
  matrices, and `rtm sync` builds the RTM rows.

## 3. Requirement quality (ISO/IEC/IEEE 29148 characteristics)

**Necessary, unambiguous, singular, verifiable, feasible, traceable**, and implementation-free at BRD/FRD level.
- Avoid "fast", "user-friendly", "etc.", "and/or", "as appropriate". Split requirements on "and".
- "shall" = mandatory, "should" = desired, "may" = optional. Priority by MoSCoW, or Unknown.
- Acceptance criteria in Given/When/Then, with concrete values.
- Quantify quality targets (`p95 < 800 ms at 200 concurrent users`, `RPO 15 min`), or mark them TBD with the decision needed.

## 4. From legacy evidence to requirements

| Evidence in the knowledge base | Becomes |
|---|---|
| Capability / domain (transactions + jobs + data) | BRD §10 BR |
| Business rule candidate (with linked source lines) | BRD §11 RUL → FRD §5 "Business rules" → SRD §5 enforcement point |
| Screen (BMS map) + dialogue | FRD §4 UC + §7 SCR spec (fields, validations, actions) |
| PF keys / EIBAID handling | FRD §7 actions |
| Message literals | FRD §12 error and message catalogue |
| Batch job chain | BRD §7 process + FRD §9 BAT-nn + SRD §17 |
| CRUD matrix | FRD §6.4 + SRD §7 |
| Copybooks / DDL | BRD §12 entities → FRD §6.1 logical model → SRD §7 physical model and mapping |
| Reports / SYSOUT / Easytrieve | BRD §12.3 / FRD §8 RPT-nn |
| MQ / file interfaces | FRD §10 INT-nn → SRD §6 IFR-nnn |
| Security checks, user types, menu filtering | BRD §6.2 → FRD §3 and §11 → SRD §8 |

**Evidence format:** write `path:line` or `path:start-end` plus the paragraph/symbol, then run `docver.py linkify`:
`- **Source:** cbl/COSGN00C.cbl:209-257 (paragraph READ-USER-SEC-FILE)` becomes a clickable link to those lines at the
pinned commit. Don't copy the code itself into a document; the link is the evidence, and copied code goes stale.

Behaviour the business doesn't want to keep becomes an explicit `Deliberate change: …` in the FR, so
functional-equivalence testing doesn't flag it as a defect.

## 5. Section-by-section notes

**BRD**: §2 written last. §4 vision in a short paragraph. §5 KPIs with baseline/target (or TBD + decision).
§6.2 user groups from security profiles/user types in legacy systems. §7/§8 swimlane flowcharts. §10 includes business-level
non-functional needs as BRs (Category: Non-functional). §11 rules grouped by domain, all Candidates until SME-confirmed.
§16 compliance, privacy and retention (personal data, regulations, retention periods). §17 transition: equivalence, data
migration, parallel run, cutover, decommission.

**FRD**: §2 context diagram. §4 journeys, use-case overview diagram, UC blocks with sequence diagrams for non-trivial flows.
§5 FR blocks with every field (actor, preconditions, main/alternate/error flows, rules, Given/When/Then). §6 logical ER,
validation rules, state diagrams for entity lifecycles, CRUD. §7 one SCR per screen + navigation diagram + accessibility
standard. §11 role × function matrix and audit behaviour. §14 equivalence scenarios for migrations.

**SRD**: §2 context, §3 components + sequence diagrams, §4 runtime versions, environments, deployment diagram.
§5 SR blocks by component with a Verification method. §6 API/event contracts. §7 physical model, field mapping, migration,
backup/retention. §8–§16 one section per quality area: numbers or TBD + decision, never invented. §17 batch and
transactions. §18 legacy → target mapping covering every artifact in scope + waves/cutover. §21 ADRs.

## 6. Sizing and slicing

- One BRD per program of work is usual, with capabilities as §10 subsections. For large estates, write one document set per domain
  (from `domains.md`), plus a short umbrella BRD for objectives and scope.
- Each downstream document pins its upstream versions in `derived_from`. `validate` flags them as STALE when upstream moves.
- Generate in passes: skeleton, then domain by domain, validating as you go. For subagents, reserve ID ranges per domain.
