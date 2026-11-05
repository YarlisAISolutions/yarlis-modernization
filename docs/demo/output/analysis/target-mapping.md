# Legacy → target mapping (draft)

Target: React SPA + Spring Boot services + Spring Batch + DB2. Suggested names are heuristics from screen titles
and data resources: rename to business terms. Copy reviewed rows into SRD §18.1 (data: §7.2) and record choices as ADRs (§21).

## Online (CICS) → React + REST

| Legacy program | TRANSID | Kind | BMS map | Screen title | React page / route | Spring Boot service | REST endpoints (draft) | Navigates to | Unit of work |
|---|---|---|---|---|---|---|---|---|---|
| COSGN00C | CC00 | screen | COSGN00/COSGN0A | — | `Cosgn0aPage` at `/cosgn00c` | usrsec-service | GET /api/usrsecs/{id} | COADM01C, COMEN01C | implicit (task end) |
| COUSR01C | CU01 | screen | COUSR01/COUSR1A | Add User | `AddUserPage` at `/add-user` | usrsec-service | POST /api/usrsecs | COADM01C, COSGN00C | implicit (task end) |

## Batch (JCL) → Spring Batch

| Job | Step | Program | COND | Target (draft) | Spring Batch job |
|---|---|---|---|---|---|

## Data stores → DB2

| Legacy store | Dataset | Target | Note |
|---|---|---|---|
| CICS FILE USRSEC | AWS.M2.CARDDEMO.USRSEC.VSAM.KSDS | table `USRSEC` | VSAM KSDS → DB2 table |

Field-level drafts: `data-mapping.md`.
