#!/usr/bin/env bash
# End-to-end self-test of the three skill scripts against the synthetic fixture in tests/fixtures/mini.
# Usage: tests/selftest.sh   (needs python3 and git; writes only to a temp dir)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
S="$ROOT/.claude/skills"
INV="$S/legacy-code-analysis/scripts/inventory.py"
MAP="$S/mainframe-modernization/scripts/mapgen.py"
D="$S/requirements-docs/scripts/docver.py"
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
ok() { echo "ok   $*"; }
fail() { echo "FAIL $*"; exit 1; }

# --- analysis
cp -R "$ROOT/tests/fixtures/mini" "$W/src"
python3 "$INV" scan --src "$W/src" --out "$W/analysis" > /dev/null
python3 - "$W/analysis/inventory.json" <<'PY' || exit 1
import json, sys
inv = json.load(open(sys.argv[1]))
s, p = inv["summary"], inv["programs"]
def need(cond, msg):
    if not cond:
        print("FAIL", msg); sys.exit(1)
    print("ok  ", msg)
need(s["programs"] == 3 and s["transactions"] == 2 and s["jobs"] == 1 and s["screens"] == 1 and s["tables"] == 1, f"counts {s}")
need(s["unresolved"] == 0, "no unresolved references")
need("MENU01" in p["ACCTUPD"]["xctl"], "dynamic XCTL resolved from VALUE literal")
need(p["ACCTUPD"]["cics_files"].get("ACCTDAT") == "RU", "CICS file CRUD (READ UPDATE + REWRITE) = RU")
need(p["ACCTPOST"]["sql_tables"].get("ACCOUNT") == "U", "embedded SQL UPDATE detected")
need(p["ACCTPOST"]["batch_files"].get("TRANIN") == "R", "batch file via SELECT/ASSIGN + OPEN INPUT")
need(any(m["text"].startswith("Credit limit") for m in p["ACCTUPD"]["messages"]), "user message extracted")
need("JOB:POSTJOB" in p["ACCTPOST"]["called_by"], "job → program link")
need([f["java"] for f in inv["copybooks"]["ACCTREC"]["fields"] if f["name"] == "ACCT-CREDIT-LIMIT"] == ["BigDecimal"], "COMP-3 → BigDecimal")
PY
python3 "$INV" slice --inventory "$W/analysis/inventory.json" --root AU01 | grep -q '"ACCTUPD"' && ok "slice by transaction"
python3 "$MAP" --inventory "$W/analysis/inventory.json" > /dev/null && grep -q "UpdateAccountPage" "$W/analysis/target-mapping.md" && ok "mapgen names page from screen title"

# --- requirements documents
cd "$W"
git init -q -b main && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
python3 "$D" init --type context --dir docs/requirements --project "Mini" --owner "Test" --src "$W/src" > /dev/null
python3 "$D" new-feature --module accounts --feature account-update > /dev/null
F=docs/requirements/accounts/account-update
[ -f $F/BRD.md ] && [ -f $F/FRD.md ] && [ -f $F/SRD.md ] && ok "new-feature scaffold"
grep -q '^doc_id: FRD-ACCOUNTS-ACCOUNT-UPDATE' $F/FRD.md && ok "doc_id derived from module/feature"
python3 - "$F/BRD.md" <<'PY'
import sys, re
p = sys.argv[1]; t = open(p).read()
t = t.replace("|---|---|---|---|---|---|\n\n## 6.", "|---|---|---|---|---|---|\n| BO-01 | Keep accounts current | Unknown | Unknown | Unknown | Unknown |\n\n## 6.", 1)
t = t.replace("## 11. Business Rules and Policy Constraints",
  "### BR-001: Update an account\n- **Statement:** Staff can change an account's credit limit.\n- **Supports:** BO-01\n"
  "- **Priority:** Unknown (proposed: Must)\n- **Basis:** Derived from code (candidate)\n- **Source:** cbl/ACCTUPD.cbl:24-31\n\n"
  "## 11. Business Rules and Policy Constraints\n\n### RUL-001: Credit limit ceiling\n- **Rule:** The credit limit cannot exceed 999,999.\n"
  "- **Source:** cbl/ACCTUPD.cbl:25\n- **Validation status:** Candidate\n- **Applies to:** BR-001\n")
open(p, "w").write(t)
PY
python3 "$D" linkify $F > /dev/null && grep -q 'ACCTUPD.cbl#L24-L31' $F/BRD.md && ok "linkify to line anchors"
python3 - "$D" <<'PY' && ok "evidence regex: parentheses, backticks, no truncation, no version numbers"
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("d", sys.argv[1]); d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
ctx = {"repo_url": "https://h/o/r", "repo_ref": "abc"}
out = d.linkify_text("(cbl/A.cbl:110-112) (`cpy/B.cpy:21`) v1.2.3:4\n", ctx, Path("."))[0]
assert "#L110-L112))" in out and "[`cpy/B.cpy:21`](https://h/o/r/blob/abc/cpy/B.cpy#L21))" in out and "1.2.3:4" in out and "](https://h/o/r/blob/abc/1.2.3" not in out, out
PY
before=$(md5sum $F/BRD.md 2>/dev/null || md5 -q $F/BRD.md); python3 "$D" linkify $F > /dev/null
after=$(md5sum $F/BRD.md 2>/dev/null || md5 -q $F/BRD.md); [ "$before" = "$after" ] && ok "linkify is idempotent"
python3 "$D" trace $F --inject > /dev/null
python3 "$D" validate $F > "$W/v.txt" || { cat "$W/v.txt"; fail "validate has errors"; }
ok "validate (no errors)"
python3 "$D" index docs/requirements > /dev/null && python3 "$D" check docs/requirements > /dev/null && ok "index + check"
git add -A && git -c user.email=t@t -c user.name=t commit -qm docs
echo "- extra" >> $F/BRD.md
python3 "$D" bumpcheck --base HEAD docs/requirements > /dev/null && fail "bumpcheck should fail without a bump" || ok "bumpcheck catches unbumped edit"
git checkout -q -- $F/BRD.md
python3 "$D" bump $F/BRD.md --summary "test change" --sections 10 > /dev/null && echo "- extra" >> $F/BRD.md
python3 "$D" bumpcheck --base HEAD docs/requirements > /dev/null && ok "bump → bumpcheck passes; history: $(ls $F/history)"
python3 "$D" validate $F/FRD.md | grep -q STALE && ok "FRD flagged STALE after BRD bump"
python3 "$D" new-feature --module accounts --feature account-update --docs rtm,gap > /dev/null && python3 "$D" rtm sync $F | grep -q "2 rows" && ok "rtm sync"
echo "all self-tests passed"
