# Prompt: generate the FRD

```markdown
## 1. Role
Act as a senior business analyst and QA lead.

## 2. Context
See docs/requirements/PROJECT-CONTEXT.md.

## 3. Task
Derive the Functional Requirements Document from docs/requirements/<module>/<feature>/BRD.md (version [X.Y.Z]).

## 4. Scope
Same slice as the BRD, unless stated: [...]

## 5. Inputs
BRD.md, the analysis knowledge base (screens.md, program cards, rules, findings), UX notes [LINKS or none].

## 6. Deliverables
docs/requirements/<module>/<feature>/FRD.md (standard 17-section structure), with derived_from pinned to the BRD version.

## 7. Rules
- Every FR traces to at least one BR (and to the RUL it applies). Every FR has actor, preconditions, main flow,
  alternate and error flows, business rules, and Given/When/Then acceptance criteria.
- Screens: one SCR block per legacy screen, with fields (length, validation, legacy field), actions
  (legacy key mapped to a new control) and messages; plus a navigation diagram and the accessibility standard.
- Behaviour that changes on purpose is written as "Deliberate change: ...", so equivalence tests don't flag it.
- Required diagrams: context (§2), use cases (§4), logical ER (§6.1), navigation (§7); sequence diagrams for non-trivial use cases.

## 8. Verification and report
Run linkify, trace --inject and validate. Report the FR coverage of the BRs, any BRs without FRs, and open questions.
```
