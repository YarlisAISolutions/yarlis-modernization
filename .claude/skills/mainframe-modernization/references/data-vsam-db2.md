# Data: copybooks, VSAM, IMS and DB2 → DB2 (target)

## First decision: which DB2

| Option | When | Watch out |
|---|---|---|
| **DB2 for z/OS** (data stays on the mainframe, apps move off) | Other mainframe workloads still use the data; data gravity; early waves | Network latency per call (avoid chatty access; use set-based SQL), DRDA/JDBC Type 4 licensing, EBCDIC CCSID, package/plan management for static SQL |
| **Db2 LUW / Db2 on cloud** (data moves with the apps) | Full exit from the mainframe | Collation differences (EBCDIC vs ASCII/Unicode ordering), data type differences, migration and reconciliation of all history |
| Both (coexistence via replication: Q Replication, IIDR/CDC) | Strangler migration over several waves | Two-way sync conflicts; define the system of record per entity per wave |

Record it as an ADR in SRD §21 with the decision drivers; it changes SRD §4, §7, §10, §11 and §17.

## Copybook / VSAM → table rules

| Legacy | Target | Rule |
|---|---|---|
| KSDS key (`KEYS(len off)`) | `PRIMARY KEY` | Take the field(s) at that offset; composite keys are common |
| AIX / PATH | secondary `INDEX` (unique if `UNIQUEKEY`) | |
| `PIC X(n)` | `CHAR(n)` for codes/fixed; `VARCHAR(n)` for names/text | Trim trailing spaces on load; decide if empty = `NULL` or `''` |
| `PIC 9(n)` / `S9(p)V9(s)` / `COMP-3` | `DECIMAL(p,s)`; `INTEGER`/`BIGINT` for counters and surrogate-like IDs | Keep precision exactly; Java `BigDecimal` for money, never `double` |
| `COMP`/`BINARY` | `SMALLINT`/`INTEGER`/`BIGINT` | Check the unsigned range |
| Dates in `X(10)`, `9(8)`, Julian `9(7)`, `9(6)` | `DATE` / `TIMESTAMP` | State format, sentinel values (`00000000`, `99999999`, LOW-VALUES), century window, and how invalid dates are handled during migration |
| `88` code domain | `CHAR(n)` + `CHECK` constraint, or a reference table | Java enum with converter |
| `OCCURS n` | Child table (`parent_key`, `seq`, fields) | Unless always read/written whole and never queried (then JSON/CLOB, with an ADR) |
| `OCCURS DEPENDING ON` | Child table; row count = counter field | Drop the counter column (derive it) |
| `REDEFINES` | (a) discriminator + nullable columns, (b) subtype tables, (c) separate tables per record type | Find the field that decides which layout applies (record type code) |
| Multiple record types in one file | One table per record type, or header/detail tables | |
| `FILLER` | Drop, after confirming with data profiling that it is empty | |
| `LOW-VALUES`/`HIGH-VALUES`/spaces as "no value" | `NULL` | Make this a documented data-migration rule (DR-nnn) |
| Signed zoned/packed with invalid nibbles | Reject or default per rule | Profile the data first |
| IMS segment hierarchy | Table per segment; parent key as FK; sequence field preserved | GN/GNP traversal → ordered queries/joins |

`mapgen.py` produces a first mechanical draft (`docs/analysis/data-mapping.md`): column names without the common prefix,
DB2/Java types from PIC. Treat it as a starting point for SRD §7.2, not a design.

## Encoding and ordering

- EBCDIC → Unicode conversion with the right CCSID (037, 1140, 500, 273…); packed and binary fields must be converted
  **per field from the copybook**, never as a whole-record codepage conversion.
- Sort/compare order changes: in EBCDIC lowercase < uppercase < digits; in ASCII/Unicode digits < uppercase < lowercase.
  Any logic or report that depends on key order (control breaks, browse ranges, `>=` start keys) must be checked.

## Transactions and concurrency on DB2

| Legacy | Target |
|---|---|
| CICS unit of work (task) / `SYNCPOINT` | `@Transactional` service method |
| Batch commit every N records | Chunk commit interval |
| `READ … UPDATE` lock across a screen | Optimistic locking (`version` column or row-change timestamp `ROW CHANGE TIMESTAMP`) |
| Isolation CS (default) | `READ_COMMITTED`; DB2 currently-committed semantics; use `UR` only for reports that tolerate dirty reads |
| `CURSOR WITH HOLD` across commits | Keyset-paginated reader (`WHERE key > :last ORDER BY key FETCH FIRST n ROWS ONLY`) |
| SQLCODE −911/−913 (deadlock/timeout) | Retry with backoff for idempotent operations (Spring Retry) |

## Data migration (SRD §7.3)

1. Profile the source data (null-likes, invalid dates/numbers, orphans, duplicate keys, REDEFINES distribution).
2. Write transformation rules as DR-nnn items, each with a test.
3. Unload (DB2 UNLOAD / DSNTIAUL / REPRO), transfer as binary, convert with copybook-driven tooling, load (Db2 LOAD/IMPORT, or batch inserts).
4. Reconcile: row counts per table, control totals (sum of balances per category), and sampled field-level comparison;
   tolerances are zero for money.
5. Rehearse the full migration at least twice; measure duration against the cutover window (BRD §17).
