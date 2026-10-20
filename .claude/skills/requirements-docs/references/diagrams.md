# Diagrams (Mermaid)

Use Mermaid in fenced ```` ```mermaid ```` blocks. It renders in GitHub, GitLab, VS Code, Confluence
(with a macro) and most Markdown viewers, needs no installed tool, and diffs as text between versions.
Every diagram gets a one-line caption above it saying what it shows, and the prose still has to stand on
its own without the diagram.

## Which diagram where

| Need | Mermaid type | Typical section |
|---|---|---|
| System context (actors, system, external systems, stores) | `flowchart LR` | BRD §7, FRD §2, SRD §2 |
| Business process with responsibilities | `flowchart TD` with one `subgraph` per actor (swimlanes) | BRD §7, §8 |
| Use-case overview (UML use case) | `flowchart LR` with actor nodes `(("Actor"))` and use cases `(["Use case"])` | FRD §4 |
| Interaction over time (UML sequence) | `sequenceDiagram` | FRD §4 per UC, SRD §3 |
| Screen navigation / lifecycle (UML state machine) | `stateDiagram-v2` | FRD §7 (navigation), FRD §6.3 (entity states), BRD §11 state rules |
| Domain/class model (UML class) | `classDiagram` | FRD §6.1 (alternative to ER), SRD §3 |
| Data model | `erDiagram` | BRD §12.2 (conceptual), FRD §6.1 (logical), SRD §7.1 (physical) |
| Components (UML component / C4 container) | `flowchart LR` with `subgraph` per tier | SRD §3 |
| Deployment (UML deployment) | `flowchart TB` with `subgraph` per node/environment | SRD §4 |
| Batch job chain | `flowchart TD` | FRD §9, SRD §17 |
| Migration plan | `gantt` | SRD §18.2 |

Required minimums (checked by `docver.py validate`): BRD §7, §8, §12; FRD §2, §4, §6, §7; SRD §2, §3 (two), §4, §7, §17.

Mermaid has no native UML use-case or component diagram. The flowchart patterns below are the conventional stand-ins.

## Patterns

Context:
```mermaid
flowchart LR
  cardholder(("Cardholder")) --> web["Card management web app"]
  clerk(("Back-office clerk")) --> web
  web --> api["Card services (Spring Boot)"]
  api --> db[("DB2")]
  api <--> auth["Card network authorization"]
  sched["Batch scheduler"] --> batch["Batch jobs (Spring Batch)"] --> db
```

Swimlane process:
```mermaid
flowchart TD
  subgraph Customer
    A["Submits transaction"]
  end
  subgraph Operations
    B["Daily posting run"] --> C{"Valid?"}
    C -- yes --> D["Update balance"]
    C -- no --> E["Write to reject report"]
  end
  A --> B
```

Use-case overview:
```mermaid
flowchart LR
  admin(("Admin user"))
  user(("Regular user"))
  uc1(["UC-01 Sign on"])
  uc2(["UC-02 View account"])
  uc3(["UC-05 Maintain users"])
  user --- uc1
  user --- uc2
  admin --- uc1
  admin --- uc3
```

Sequence (pseudo-conversational CICS replaced by REST):
```mermaid
sequenceDiagram
  actor U as User
  participant UI as React app
  participant API as account-service
  participant DB as DB2
  U->>UI: Enter account id, press Enter
  UI->>API: GET /accounts/{id}
  API->>DB: SELECT ... FROM ACCOUNT WHERE ACCT_ID = ?
  alt found
    DB-->>API: row
    API-->>UI: 200 AccountDto
  else not found
    API-->>UI: 404 {code: "ACCT_NOT_FOUND"}
    UI-->>U: "Account not found"
  end
```

Screen navigation:
```mermaid
stateDiagram-v2
  [*] --> SignOn
  SignOn --> MainMenu: valid user
  SignOn --> AdminMenu: admin user
  MainMenu --> AccountView: option 1
  AccountView --> MainMenu: F3 / Back
  MainMenu --> SignOn: F3 / Sign off
```

ER (attribute types are single words; put lengths in the comment):
```mermaid
erDiagram
  CUSTOMER ||--o{ ACCOUNT : owns
  ACCOUNT ||--o{ CARD : "has"
  ACCOUNT {
    decimal acct_id PK "DECIMAL(11)"
    char active_status "Y/N"
    decimal curr_bal "DECIMAL(12,2)"
  }
```

Components:
```mermaid
flowchart LR
  subgraph Client
    spa["React SPA"]
  end
  subgraph Services["Spring Boot services"]
    acct["account-service"]
    card["card-service"]
    txn["transaction-service"]
  end
  subgraph Batch["Spring Batch"]
    post["daily-posting-job"]
  end
  subgraph Data
    db2[("DB2")]
  end
  spa --> acct & card & txn
  acct & card & txn --> db2
  post --> db2
```

## Syntax traps (docver.py validate catches the first three)

- Quote labels containing `(`, `)`, `:`, `/`, `#` or punctuation: `A["Read file (VSAM)"]`.
- `end` is reserved in flowcharts; use `End1` or `done` as the node id.
- `erDiagram` attribute types can't contain `(n)`: write `decimal amount "DECIMAL(12,2)"`.
- Node ids are letters/digits/underscore only; put the readable name in the label.
- Keep diagrams under ~25 nodes; split by capability rather than drawing the whole estate.
- `classDiagram` generics use `~`: `List~Card~`.

## Optional rendering check

When Node is available, `npx -y @mermaid-js/mermaid-cli -i doc.md -o out.md` renders every block and fails
on syntax errors (it downloads a headless browser the first time). Run it before a baseline (major) version.
