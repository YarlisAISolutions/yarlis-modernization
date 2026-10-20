# Prompt: analyze legacy code

```markdown
## 1. Role
Act as a senior mainframe analyst and business analyst.

## 2. Context
See docs/requirements/PROJECT-CONTEXT.md. (If it doesn't exist yet: Project [NAME]; source at [PATH];
target stack [STACK | Unknown]; owner [NAME | Unknown].)

## 3. Task
Analyze the existing code for [CAPABILITY] and build the analysis knowledge base.

## 4. Scope
- Slice: transactions [CC00, CU00 ...], jobs [JOBNAME ...], programs [PGM ...]
- Out of scope: [...]

## 5. Inputs
Source tree at [PATH] (COBOL, copybooks, JCL/PROCs, BMS, CSD, DDL/DCLGEN, control cards, scheduler definitions).

## 6. Deliverables
docs/analysis/: inventory (scan), slice file list, program cards, system-overview.md with diagrams,
rules/<domain>.md (business rule candidates), findings.md (defects and anomalies), analysis-notes.md (coverage, open questions).

## 7. Rules
- Use the legacy-code-analysis skill: scan, then close the unresolved references, then slice, then read and extract.
- Every rule, flow and finding links to the exact source lines; no pasted code.
- Rules are Candidates with a confidence level; business language first, identifiers only in the evidence.
- Missing source members, dynamic calls you couldn't resolve and contradictions go to open questions.

## 8. Verification and report
Report: counts (programs, transactions, jobs, tables), unresolved references left, rules and findings found,
coverage per program, and the top open questions.
```
