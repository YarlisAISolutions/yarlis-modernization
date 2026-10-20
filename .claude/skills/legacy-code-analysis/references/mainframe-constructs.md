# Reading mainframe source: what each construct means for requirements

Use this when a program card or a source file shows a construct and you need to know what it means
for the business (BRD), the behaviour (FRD) or the target design (SRD).

## Contents
1. COBOL program structure
2. CICS (online)
3. BMS screens
4. JCL and batch
5. Data stores: VSAM, sequential/GDG, DB2, IMS
6. Messaging: MQ
7. Copybooks and PIC clauses
8. Other legacy languages

## 1. COBOL program structure

| Construct | Where | Meaning for requirements |
|---|---|---|
| `IDENTIFICATION DIVISION` / `PROGRAM-ID` | top | Program name, the unit the inventory tracks. Header comments often state the business purpose: quote them. |
| `ENVIRONMENT DIVISION` / `SELECT f ASSIGN TO dd` | batch | Logical file `f` bound to JCL DD `dd`; the JCL decides the real dataset. |
| `DATA DIVISION` / `FD`, `WORKING-STORAGE`, `LINKAGE SECTION` | | Record layouts (often via `COPY`). `LINKAGE` = data passed in (COMMAREA, CALL parameters). |
| `88` level | data | Named condition = enumerated domain value. Usually a business code (status, type) or a flag. A business rule candidate when the name is business-like (`ACCT-ACTIVE`), not when it is technical (`ERR-FLG-ON`). |
| `PROCEDURE DIVISION` paragraphs / `PERFORM` | logic | Paragraph names are the best hint of intent (`1200-EDIT-MAP-INPUTS`). The PERFORM tree in the program card is the control flow. |
| `EVALUATE` / `IF` | logic | Decisions. Business decisions become RUL (Decision/Validation); technical checks (FILE STATUS, SQLCODE, EIBRESP) become error-handling requirements. |
| `COMPUTE` / `ADD` / `MULTIPLY` … `ROUNDED` | logic | Calculations: capture formula, precision, rounding, and the order of operations exactly. |
| `MOVE 'text' TO WS-MESSAGE` | logic | User-visible message: a validation rule and a message-catalogue entry. |
| `CALL 'PGM' USING …` | logic | Static subprogram call (shared routine: date, validation, calculation). `CALL WS-VAR` is dynamic: the target depends on data. |
| `GOBACK` / `STOP RUN` / `RETURN-CODE` | end | Batch return codes drive JCL step conditions. |

Fixed format: columns 1–6 sequence, 7 indicator (`*` `/` comment, `-` continuation, `D` debug), 8–72 code, 73–80 ignored.

## 2. CICS (online)

| Command | Meaning | Modern equivalent (default) |
|---|---|---|
| `RETURN TRANSID(t) COMMAREA(c)` | **Pseudo-conversational** end of a screen interaction: the task ends, state is kept in COMMAREA until the user presses a key, then transaction `t` restarts the program. `EIBCALEN = 0` means first entry. | Stateless REST call per user action; state lives in the React client (or a server-side session/token). |
| `XCTL PROGRAM(p)` | Transfer control to `p`, no return (navigation to another screen). | Client-side route change. |
| `LINK PROGRAM(p)` | Call `p` and come back (shared service). | Service method / internal API call. |
| `SEND MAP / RECEIVE MAP` | Show / read a BMS screen. | React page render / form submit. |
| `EIBAID` / `DFHENTER`, `DFHPF3`, `DFHCLEAR` | Which key the user pressed. PF3 usually = back/exit, PF7/PF8 = page up/down, ENTER = submit. | Buttons, keyboard shortcuts, pagination controls. |
| `READ / WRITE / REWRITE / DELETE FILE(f)` | VSAM record I/O; `READ … UPDATE` locks the record until REWRITE/SYNCPOINT. | Repository calls; locking → optimistic concurrency. |
| `STARTBR / READNEXT / READPREV / ENDBR` | Browse (list screens, paging). | Keyset pagination query. |
| `SYNCPOINT` / `SYNCPOINT ROLLBACK` | Commit / back out the unit of work. | `@Transactional` boundary. |
| `HANDLE CONDITION`, `RESP(…)` | Error handling (NOTFND, DUPREC…). | Exceptions mapped to HTTP status + message. |
| `ASSIGN USERID`, `ASSIGN APPLID` | Who/where. | Security context. |
| `START TRANSID … INTERVAL` | Asynchronous / scheduled task. | Async job, message, scheduler. |
| `WRITEQ TS / READQ TS` | Temporary storage queue (scratchpad, often paging state). | Client state, cache, or table. |
| `WRITEQ TD` | Transient data (logging, trigger to batch). | Log/event/message. |

Online entry points come from the CICS CSD (`DEFINE TRANSACTION(t) PROGRAM(p)`). When there is no CSD,
infer them from `RETURN TRANSID` literals in each program card.

## 3. BMS screens

`DFHMSD` = mapset (the source member), `DFHMDI` = map (one screen), `DFHMDF` = field.
`ATTRB`: `UNPROT` = input, `PROT`/`ASKIP` = output or label, `NUM` = numeric only, `BRT` = highlighted,
`DRK` = hidden (passwords), `IC` = initial cursor, `FSET` = always sent back. `INITIAL='…'` = literal label.
`POS=(row,col)` and `LENGTH` give the 24×80 layout. A named output field with no INITIAL is filled by the
program. Fields named `ERRMSG`/`MSG` show messages. The generated symbolic map copybook (`cpy-bms/`) gives
the program-side names with suffixes `L` (length), `F` (flag), `A` (attribute), `I` (input), `O` (output).

## 4. JCL and batch

| Statement | Meaning |
|---|---|
| `//name JOB` | A job: a schedulable unit. The scheduler (CA-7, Control-M, TWS, ZEKE) decides when and in what order jobs run; its definitions are the batch calendar. |
| `//step EXEC PGM=p` | A step running program `p`. `EXEC procname` runs a cataloged PROC (expand it). |
| `IKJEFT01` + `SYSTSIN: RUN PROGRAM(p) PLAN(x)` | A DB2 batch program `p` (the inventory resolves this). |
| `DD DSN=…,DISP=(NEW,CATLG,DELETE)` | Creates a dataset. `SHR` = read, `OLD` = exclusive update, `MOD` = append. |
| `DSN=X.Y(+1)` / `(0)` | GDG: `(+1)` new generation, `(0)` current. A dated history of a file; often an audit/retention requirement. |
| `COND=` / `IF RC … THEN` | Step runs or is skipped based on prior return codes: business-relevant error paths. |
| `SORT` / `ICETOOL` with `SYSIN` control cards | Sorting, merging, filtering, summarizing: often hidden business logic (`INCLUDE COND=`, `SUM FIELDS=`). Read the control cards. |
| `IDCAMS` `DEFINE/DELETE/REPRO` | VSAM housekeeping or copy/load. Usually technical. |
| `DFSRRC00` `PARM='DLI,pgm,psb'` | IMS batch program. |
| `SYSOUT=*` | Report/print output: candidate report requirement. |

## 5. Data stores

- **VSAM KSDS**: keyed file (key offset/length in IDCAMS `KEYS(len off)`) → table with that primary key.
  **AIX/PATH** → secondary index. **ESDS** → append-only log. **RRDS** → slot-numbered.
- **Sequential / GDG**: flat files between batch steps; interface files with partners.
- **DB2**: `EXEC SQL` in programs; DDL in `ddl/`, host-variable layouts in DCLGEN (`dcl/`).
  `SQLCODE` 0 OK, +100 not found, −803 duplicate key, −811 multiple rows, −911/−913 deadlock/timeout.
  Cursor `WITH HOLD` survives commit (batch commit intervals). Isolation `UR/CS/RS/RR`.
- **IMS DB**: hierarchical; DBD = database structure (segments, parents), PSB/PCB = program's view.
  `CALL 'CBLTDLI' USING GU|GN|GNP|ISRT|REPL|DLET` = read unique/next/insert/replace/delete.

## 6. Messaging: MQ

`MQOPEN/MQPUT/MQGET/MQCLOSE` calls; queue names in working storage or config. Each queue pair is an
interface (INT-nn in the FRD, IFR in the SRD): partner, direction, message layout (copybook), sync/async.

## 7. Copybooks and PIC clauses

| PIC / USAGE | Meaning | DB2 | Java |
|---|---|---|---|
| `X(n)` | text n bytes | `CHAR(n)` / `VARCHAR(n)` | `String` |
| `9(n)` | unsigned zoned number | `DECIMAL(n,0)` / `INTEGER` / `BIGINT` | `int`/`long` |
| `S9(p)V9(s)` | signed, implied decimal point | `DECIMAL(p+s,s)` | `BigDecimal` |
| `… COMP-3` | packed decimal (2 digits/byte) | `DECIMAL` | `BigDecimal` |
| `… COMP` / `COMP-4` / `BINARY` | binary integer | `SMALLINT`/`INTEGER`/`BIGINT` | `short`/`int`/`long` |
| `OCCURS n` | repeating group | child table | `List<…>` |
| `REDEFINES` | same bytes, alternate layout (variant record, type flag usually decides) | separate columns/tables or discriminator | sealed types / subclasses |
| `FILLER` | unused/reserved bytes | drop (check it is really unused) | — |

Dates are usually `X(10)` or `9(8)` (YYYYMMDD), sometimes Julian `9(7)` (YYYYDDD) or `9(6)` with a century window: always state the format.

## 8. Other legacy languages (same method, different syntax)

- **PL/I**: `PROC`, `CALL`, `%INCLUDE`, `EXEC SQL/CICS` like COBOL; `DCL … FIXED DEC(p,s)` = packed decimal.
- **Assembler (HLASM)**: `CSECT`, `CALL`/`LINK EP=`, macros; usually utilities: document the interface, not internals.
- **Easytrieve**: report programs: `FILE`, `JOB INPUT`, `REPORT`: each is a report requirement.
- **REXX / CLIST**: automation and glue; often operational, sometimes business (file routing).
- **Natural/Adabas**: `READ/FIND/STORE/UPDATE` on DDMs (Adabas files); maps = screens.
- **RPG (IBM i)**: F-specs = files, D-specs = data, C-specs/free-form = logic; display files = screens.
- **Java / .NET / Python / JS**: the inventory lists imports, classes, endpoints and SQL tables; read controllers/handlers for behaviour, services for rules, repositories/entities for data.
