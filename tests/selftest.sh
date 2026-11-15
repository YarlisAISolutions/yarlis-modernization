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
python3 "$D" bump $F/BRD.md --summary "test change" --dry-run | grep -q 'BRD.md: 0.1.0 -> 0.2.0' && [ ! -e $F/history ] \
  && git diff --quiet -- $F/BRD.md && ok "bump --dry-run prints the next version and writes nothing" || fail "bump --dry-run"
python3 "$D" bump $F/BRD.md --summary "test change" --sections 10 > /dev/null && echo "- extra" >> $F/BRD.md
python3 "$D" bumpcheck --base HEAD docs/requirements > /dev/null && ok "bump → bumpcheck passes; history: $(ls $F/history)"
python3 "$D" validate $F/FRD.md | grep -q STALE && ok "FRD flagged STALE after BRD bump"
python3 "$D" new-feature --module accounts --feature account-update --docs rtm,gap > /dev/null && python3 "$D" rtm sync $F | grep -q "2 rows" && ok "rtm sync"

# --- schema-diff: a DDL change → changed columns, affected programs, affected requirement IDs
git add -A && git -c user.email=t@t -c user.name=t commit -qm "before schema change"
sed 's/CURR_BAL     DECIMAL(12,2) NOT NULL,/CURR_BAL     DECIMAL(13,2) NOT NULL,\
    LAST_TXN_TS  TIMESTAMP,/' src/ddl/ACCOUNT.ddl > "$W/ddl.tmp" && mv "$W/ddl.tmp" src/ddl/ACCOUNT.ddl
mkdir -p "$W/req-sd/a/b" && printf '## 10. X\n\n### BR-007: Post transactions\n- **Source:** cbl/ACCTPOST.cbl:3\n\n### BR-008: Other\n- nothing\n' > "$W/req-sd/a/b/BRD.md"
python3 "$INV" schema-diff --src src --base HEAD --inventory "$W/analysis/inventory.json" --requirements "$W/req-sd" --out "$W/sd.md" > /dev/null
grep -q 'column changed: CURR_BAL DECIMAL(12,2) NOT NULL → DECIMAL(13,2) NOT NULL' "$W/sd.md" && grep -q 'column added: LAST_TXN_TS TIMESTAMP' "$W/sd.md" && ok "schema-diff: column changes"
grep -q '| ACCTPOST | cbl/ACCTPOST.cbl | ACCOUNT | ACCOUNT:U |' "$W/sd.md" && ok "schema-diff: affected program from the CRUD matrix"
grep -q 'BRD.md | BR-007 | ACCTPOST' "$W/sd.md" && ! grep -q 'BR-008' "$W/sd.md" && ok "schema-diff: affected requirement IDs only"
git add -A && git -c user.email=t@t -c user.name=t commit -qm "schema change"
python3 "$INV" schema-diff --src src --base HEAD~1 --head HEAD --inventory "$W/analysis/inventory.json" --json | grep -q '"kind": "changed"' && ok "schema-diff between two refs"
python3 "$INV" schema-diff --src src --base HEAD --inventory "$W/analysis/inventory.json" | grep -q '^0 tables' && ok "schema-diff: no change → empty report"

# --- convert: Word and PDF inputs → Markdown (MOD-9). The PDF cases use a fake pdftotext / an empty PATH.
mkdir -p "$W/in/sub" "$W/fakebin"
python3 "$ROOT/tests/make_docx.py" "$W/in/sub/spec.docx"
python3 "$D" convert "$W/in" > /dev/null || fail "convert: docx"
python3 - "$ROOT/tests" "$W/in/sub/spec.docx.md" <<'PY' || exit 1
import sys
sys.path.insert(0, sys.argv[1])
import make_docx
got = open(sys.argv[2], encoding="utf-8").read().split("\n", 2)
if not got[0].startswith("<!-- l2m convert v1: generated from spec.docx (sha256 ") or got[2] != make_docx.EXPECTED:
    print("FAIL convert: docx headings, lists, links, table, tracked changes"); print("".join(got)); sys.exit(1)
print("ok   convert: docx headings, lists, links, table, tracked changes")
PY
python3 "$D" convert "$W/in" | grep -q '^0 converted, 1 up to date, 0 skipped' && ok "convert: unchanged input is not rewritten"
printf 'hand-written\n' > "$W/in/sub/spec.docx.md"
out="$(python3 "$D" convert "$W/in")" && fail "convert: should exit 1 when a hand-written file is in the way"
grep -q 'was not written by l2m' <<< "$out" && grep -qx 'hand-written' "$W/in/sub/spec.docx.md" && ok "convert: never overwrites a hand-written .md"
printf 'x' > "$W/in/broken.docx" && printf '%%PDF-1.4\n' > "$W/in/scan.pdf"
python3 - "$W/in/sub/spec.docx" "$W/in/a-corrupt.docx" <<'PY'
import sys  # a real zip whose document.xml bytes are damaged: opens fine, fails on read (bad CRC)
data = bytearray(open(sys.argv[1], "rb").read())
i = data.index(b"<w:body>")
data[i:i + 8] = b"<w:BODY>"
open(sys.argv[2], "wb").write(bytes(data))
PY
out="$(PATH=/nonexistent "$(command -v python3)" "$D" convert "$W/in" --force)" && fail "convert: should exit 1 on a skipped file"
grep -q 'broken.docx: not a valid .docx' <<< "$out" && grep -q 'scan.pdf: PDF conversion needs pdftotext' <<< "$out" \
  && grep -q 'brew install poppler' <<< "$out" && ok "convert: broken docx and missing pdftotext are reported, not fatal"
grep -q 'a-corrupt.docx: BadZipFile' <<< "$out" && grep -q 'converted .*sub/spec.docx' <<< "$out" \
  && ok "convert: a corrupt file inside a valid zip is skipped and later files still convert"
rm "$W/in/a-corrupt.docx"
printf '#!/bin/sh\nprintf "Page one\\n\\f1. Scope of CURR_BAL\\n"\n' > "$W/fakebin/pdftotext" && chmod +x "$W/fakebin/pdftotext"
rm "$W/in/broken.docx"
PATH="$W/fakebin:$PATH" python3 "$D" convert "$W/in" > /dev/null || fail "convert: pdf with pdftotext"
grep -q '<!-- page 2 -->' "$W/in/scan.pdf.md" && grep -q '^Page one$' "$W/in/scan.pdf.md" && ok "convert: pdf through pdftotext, one marker per page"
grep -qxF '1\. Scope of CURR_BAL' "$W/in/scan.pdf.md" && ok "convert: numbered lines escaped after the digits, underscores inside words kept"

echo "all self-tests passed"
