# Business rule extraction

How to turn code into business rules that a business person can confirm, with evidence a developer can check.

## What counts as a business rule

| Type | Looks like in code | Example (plain language) |
|---|---|---|
| Validation | `IF field = SPACES/ZERO … MOVE 'msg'`, `IF NOT NUMERIC`, range checks | "Account number is required and must be 11 digits." |
| Calculation | `COMPUTE`, `ADD … GIVING`, `ROUNDED` | "Monthly interest = category balance × rate ÷ 1200, rounded to cents." |
| Decision | `EVALUATE`/nested `IF` on business codes | "Transactions of type 02 debit the account; type 01 credit it." |
| State transition | `MOVE 'C' TO STATUS` guarded by conditions | "A card moves from Active to Blocked after 3 failed authorizations." |
| Constraint | key checks, duplicate checks, `SQLCODE -803` handling | "A user ID is unique." |
| Authorization | user type checks, menu option filtering | "Only admin users (type A) can maintain users." |
| Derivation | defaulting, lookups, cross-reference reads | "Customer is found from the card via the card cross-reference." |
| Timing | batch schedule, cut-off dates, cycle logic | "Interest is posted once per cycle, after transactions are posted." |

Not business rules (record them as error handling or technical design instead): FILE STATUS/SQLCODE/EIBRESP
plumbing, abend handling, screen attribute juggling, paging mechanics, logging.

## Method (per program or slice)

1. **Start from the program card** (`docs/analysis/programs/<PGM>.md`): paragraphs, PERFORM tree, messages,
   88-levels, data accessed. Messages and 88-levels are the fastest route to validations and code domains.
2. **Read the edit/validate paragraphs first** (names with EDIT, VALID, CHECK, VERIFY), then the
   process/update paragraphs (PROCESS, UPDATE, POST, CALC, COMPUTE), then the decision paragraphs.
3. **Follow data, not just control**: for each field written to a file/table, find where its value comes from.
   That chain is a derivation or calculation rule.
4. **Resolve copybook names** to business meanings (data dictionary) before writing the rule: write
   "credit limit", not `ACCT-CREDIT-LIMIT`.
5. **Write the rule in business language** and keep the code in the evidence:
   ```
   ### RUL-014: Sign-on requires matching password
   - **Rule:** A user may sign on only when the user ID exists and the password entered matches the stored password.
     Otherwise the screen shows "User not found" or "Wrong password" and the user stays on the sign-on screen.
   - **Type:** Validation
   - **Source:** cbl/COSGN00C.cbl:209-257 (paragraph READ-USER-SEC-FILE); messages cbl/COSGN00C.cbl:242, cbl/COSGN00C.cbl:249
   - **Validation status:** Candidate
   - **Applies to:** BR-002
   - **Confidence:** High (single, explicit IF) | Medium | Low (inferred / dynamic / dead-code suspicion)
   ```
   Cite source as `path:line` / `path:start-end` (relative to the scanned source root) and turn the references into
   hyperlinks (`docver.py linkify` in requirements-docs, using the repo URL and commit recorded by the scan). Never paste
   the COBOL into the catalogue: the link pins the exact lines at the exact commit, and a copy goes stale.
6. **Deduplicate across programs**: the same check often appears on several screens; one rule, several sources.
7. **Flag contradictions and dead code**: two programs enforcing different limits, branches that can never run,
   commented-out logic. These go to Open Questions, not silently into the rule set.
8. **Mark everything Candidate.** Only a business SME promotes a rule to SME-confirmed. Never present a
   candidate rule as confirmed fact; this is the main hallucination guard.

## Precision checklist for calculations

- Exact operand order and intermediate precision (COBOL truncates intermediates to the receiving field unless `ROUNDED`).
- Rounding mode (`ROUNDED` = half-up in COBOL; Java `BigDecimal` needs `RoundingMode.HALF_UP` explicitly).
- Sign handling and overflow (`ON SIZE ERROR`).
- Units and periods (rate in percent per year vs per month).
- Date arithmetic (`FUNCTION INTEGER-OF-DATE`, Julian dates, century windows).

These details matter because functional-equivalence tests compare outputs to the cent.

**Platform defaults** are part of the rule even though they're invisible in the code: CICS `STARTBR` without `EQUAL` positions on
the first key ≥ the given key (GTEQ), `READ` without `UPDATE` takes no lock, COBOL `MOVE` truncates silently, and a terminal may
upper-case input (`UCTRAN`). When a rule depends on one, name it in the rule and lower the Confidence until it's checked against the
real system configuration.

## Coverage tracking

Keep a short coverage table in the analysis notes so later iterations know what has been read:

| Program | Paragraphs read | Rules found | Open questions |
|---|---|---|---|
| COSGN00C | all (6/6) | RUL-014, RUL-015 | Q-3 (password case sensitivity) |
