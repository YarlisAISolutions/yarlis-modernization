# Demo: AWS CardDemo, from COBOL to a React / Spring Boot / DB2 mapping

This walkthrough runs the whole l2m pipeline on one slice of [AWS CardDemo](https://github.com/aws-samples/aws-mainframe-modernization-carddemo):
**sign-on (transaction CC00) and add user (CU01)**. You scan the mainframe source, cut the slice, draft the target mapping,
write the BRD, FRD and SRD with an agent, then build the traceability matrix (RTM) and the gap report.

Don't want to run it? The result is in [`output/`](output/):

| Output | What it is |
|---|---|
| [`output/analysis/slice.json`](output/analysis/slice.json) | The slice: 2 programs, 2 screens, 1 VSAM file, 9 copybooks |
| [`output/analysis/target-mapping.md`](output/analysis/target-mapping.md) | Draft mapping: CICS program → React page + Spring Boot service, VSAM → DB2 |
| [`output/analysis/data-mapping.md`](output/analysis/data-mapping.md) | Draft field mapping: copybook → DB2 column and Java type |
| [`BRD.md`](output/requirements/user-admin/sign-on/BRD.md) | Business requirements: 5 BRs, 7 candidate business rules, 4 risks, 6 open questions |
| [`FRD.md`](output/requirements/user-admin/sign-on/FRD.md) | Functional requirements: 3 use cases, 10 FRs, 2 screens, 16 messages |
| [`SRD.md`](output/requirements/user-admin/sign-on/SRD.md) | System requirements and the reviewed legacy → target mapping (§7.2, §18.1) |
| [`RTM.md`](output/requirements/user-admin/sign-on/RTM.md) | 36 requirements traced BR → FR → SR, each with its status in the legacy code |
| [`GAP-REPORT.md`](output/requirements/user-admin/sign-on/GAP-REPORT.md) | Two-page summary for decision makers |

Every document carries a version header and passes `docver.py validate`. Evidence links point at CardDemo source lines at the
pinned commit; no CardDemo source is copied into this repository.

The documents found real defects in the legacy code. For example, Add User saves a password as typed, but sign-on compares it
in upper case, so a user added with a lower-case password can never sign on (BRD §7, RSK-01).

## What is reproducible

| Part | Steps | Reproducible? |
|---|---|---|
| Deterministic | 1–4 and 6: fetch, init, scan, slice, map, linkify, trace, RTM sync, summary, validate | Yes, byte for byte. CI re-runs them (`scripts/check-demo.sh`) and fails if the committed output drifts. |
| Agent | 5: write the BRD, FRD, SRD and assess the RTM rows | The structure is reproducible, the wording is not. `l2m generate` validates each document and stops on errors, so a run either passes `validate` or tells you what to fix. |

The committed documents come from one recorded run with Claude Code against the prompts that `l2m generate` builds.

## Before you start

- Node 22+ (CI uses 24.22.1), Python 3.9+ and git: `l2m doctor` checks them.
- For step 5 with an agent: one of Claude Code (`claude`), GitHub Copilot CLI, Codex or Gemini CLI. Without one, step 5 uses
  the recorded output instead.
- About 15 MB of disk for CardDemo.

## 1. Fetch the code at pinned versions

Work in an empty folder. `yarlis-modernization`, `carddemo` and `demo` sit side by side, and the evidence links rely on
that layout.

```sh
mkdir l2m-demo && cd l2m-demo
export WORK="$PWD"
git clone https://github.com/YarlisAISolutions/yarlis-modernization
git -C yarlis-modernization checkout -q "$(git -C yarlis-modernization log -1 --format=%H -- docs/demo/output)"
git init -q carddemo
git -C carddemo remote add origin https://github.com/aws-samples/aws-mainframe-modernization-carddemo
git -C carddemo fetch -q --depth 1 origin 59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e
git -C carddemo checkout -q FETCH_HEAD
l2m() { node "$WORK/yarlis-modernization/bin/l2m.js" "$@"; }
```

CardDemo is pinned to commit `59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e` (2025-10-16). The clone is pinned to the
yarlis-modernization commit that last recorded `docs/demo/output`, so the templates and scripts you run are the ones that
produced it, even after `main` moves on. The `l2m` function runs the CLI from that checkout.

## 2. Set up a project repository

```sh
mkdir demo && cd demo && git init -q
l2m init --src ../carddemo/app --project "CardDemo" --owner "Demo owner" --agents claude \
  --target-stack "React + Spring Boot + DB2"
cp ../yarlis-modernization/docs/demo/output/requirements/PROJECT-CONTEXT.md docs/requirements/
```

Expected: a list of `add` lines (skills, prompts, the CI workflow, `l2m.config.json`, `docs/requirements/PROJECT-CONTEXT.md`)
and `Done (l2m <version>)`. Use `--agents copilot`, `codex` or `gemini` for another agent.

`init` asks you to fill in `PROJECT-CONTEXT.md` (users, stage, constraints). The `cp` line puts in the filled copy from this
demo. Its front matter pins evidence links to CardDemo at the commit above:

```text
source_root: "../../../carddemo/app"
repo_url: "https://github.com/aws-samples/aws-mainframe-modernization-carddemo"
repo_ref: "59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e"
```

## 3. Scan CardDemo

```sh
l2m analyze scan --src ../carddemo/app --out docs/analysis
```

Expected, at the end of the output:

```text
 "programs": 46,
 "copybooks": 65,
 "jobs": 46,
 "screens": 21,
 "transactions": 25,
 "tables": 3,
 "unresolved": 0,
 "total_loc": 23018
}

Wrote docs/analysis/inventory.json, inventory.md, callgraph.mmd, crud-matrix.md, data-dictionary.md, screens.md, batch-flows.md, programs/
```

`docs/analysis/` is the knowledge base the agent reads: one card per program, the CRUD matrix, the data dictionary, screens
and batch flows.

## 4. Cut the slice and draft the mapping

```sh
l2m analyze slice --inventory docs/analysis/inventory.json --root CC00 CU01 > docs/analysis/slice.json
l2m map --inventory docs/analysis/inventory.json --programs COSGN00C COUSR01C
```

Expected: `slice.json` lists programs `COSGN00C` and `COUSR01C`, the `USRSEC` file and 14 files to read; `map` prints
`Wrote docs/analysis/target-mapping.md and docs/analysis/data-mapping.md`. Both files match
[`output/analysis/`](output/analysis/) exactly. The mapping is a draft: COSGN00C's map has no title, so mapgen names its page
`Cosgn0aPage`; the SRD renames it `SignOnPage` (SRD §18.1).

## 5. Write the BRD, FRD and SRD, then assess them

**With an agent** (Claude Code here; the run takes several minutes per document):

```sh
l2m generate all --module user-admin --feature sign-on --title "Sign-on and add user" \
  --scope "CC00 sign-on (COSGN00C) and CU01 add user (COUSR01C)" \
  --out-of-scope "The admin and main menus (COADM01C, COMEN01C), list, update and delete user (CU00, CU02, CU03), and the USRSEC load jobs (DUSRSECJ, ESDSRRDS)" \
  --agent claude
l2m generate assess --module user-admin --feature sign-on --agent claude
```

For each document, `generate` builds the prompt (`l2m prompt brd …` prints it), runs the agent, then runs linkify,
`trace --inject`, validate and index itself. It stops on a validation error. `assess` adds `RTM.md` and `GAP-REPORT.md` and
asks the agent to fill each RTM row from the code. If the agent CLI isn't on your PATH, `generate` prints the prompt instead
and changes nothing.

**Without an agent**, use the recorded run:

```sh
mkdir -p docs/requirements/user-admin
cp -R ../yarlis-modernization/docs/demo/output/requirements/user-admin/sign-on docs/requirements/user-admin/
```

## 6. Traceability, gap report and validation

```sh
l2m docs rtm sync docs/requirements/user-admin/sign-on
l2m docs rtm summary docs/requirements/user-admin/sign-on
l2m docs index docs/requirements
l2m docs validate docs/requirements/user-admin/sign-on
l2m docs check docs/requirements
```

Expected:

- `rtm sync` prints `RTM synced: 36 rows, 0 added` (step 5 already created all 36 rows).
- `rtm summary` prints the counts table that also goes into RTM §4.1 and gap report §3: 14 implemented, 3 partially,
  19 not implemented, 36 not verified.
- `validate` prints `OK` under each of the five documents, and `check` ends with `check: OK`.

Your own agent run gives different IDs, wording and counts. Validation must still pass.

## Reading the result

This is a **baseline assessment**: the repository holds only the legacy system, so "Implemented" in the RTM means "CardDemo
already does this" (behaviour to reproduce or deliberately change), not "migrated". The SRD rows are Not implemented because
no React or Spring Boot code exists yet.

Start with the [gap report](output/requirements/user-admin/sign-on/GAP-REPORT.md), then follow its RTM IDs into the
[BRD](output/requirements/user-admin/sign-on/BRD.md). The evidence links open the exact CardDemo lines on GitHub.

## Keeping the demo current

`scripts/check-demo.sh` runs in the `selftest` workflow. It fetches CardDemo at the pinned commit, repeats steps 2–4 and 6
on the committed documents, and fails when any output differs or `docver.py validate` reports an error. After a deliberate
change to a template, `docver.py` or `mapgen.py`, refresh the output and review the diff:

```sh
L2M_UPDATE_DEMO=1 bash scripts/check-demo.sh
```
