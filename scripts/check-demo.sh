#!/usr/bin/env bash
# Re-runs the deterministic half of the CardDemo walkthrough (docs/demo/README.md) and fails when the committed output in
# docs/demo/output drifts: the scan counts, the slice, the mapping drafts, and the requirements documents after
# linkify / trace / rtm sync / rtm summary / index must be unchanged, and the documents must pass docver.py validate and check.
#
# Usage: scripts/check-demo.sh [<carddemo-checkout>]
#   With no argument it fetches CardDemo at CARDDEMO_SHA into a temp dir (needs network). A checkout you pass must be
#   clean (no edits, untracked or ignored files), at CARDDEMO_SHA, with origin set to CARDDEMO_URL (the drafts link to it).
#   L2M_UPDATE_DEMO=1 copies the regenerated files over docs/demo/output instead of failing (after a deliberate change).
set -euo pipefail
CARDDEMO_URL=https://github.com/aws-samples/aws-mainframe-modernization-carddemo
CARDDEMO_SHA=59cc6c2fd7ebd7ef7925cad552a01a4b8b6e4d5e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/docs/demo/output"
W="$(mktemp -d "${TMPDIR:-/tmp}/l2m-demo.XXXXXX")"; trap 'rm -rf "$W"' EXIT
l2m() { node "$ROOT/bin/l2m.js" "$@"; }
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }

# The same layout as the walkthrough: <work>/carddemo next to <work>/demo (PROJECT-CONTEXT.md's source_root relies on it).
if [ $# -ge 1 ]; then
  ln -s "$(cd "$1" && pwd)" "$W/carddemo"
else
  git init -q "$W/carddemo"
  git -C "$W/carddemo" remote add origin "$CARDDEMO_URL"
  git -C "$W/carddemo" fetch -q --depth 1 origin "$CARDDEMO_SHA"
  git -C "$W/carddemo" checkout -q FETCH_HEAD
fi
head="$(git -C "$W/carddemo" rev-parse HEAD)"
[ "$head" = "$CARDDEMO_SHA" ] || { echo "FAIL CardDemo is at $head, expected $CARDDEMO_SHA"; exit 1; }
dirty="$(git -C "$W/carddemo/" status --porcelain --untracked-files=all --ignored)"
[ -z "$dirty" ] || { echo "$dirty" | head -20; echo "FAIL the CardDemo checkout has local changes or extra files; use a clean one"; exit 1; }

mkdir "$W/demo" && cd "$W/demo" && git init -q
l2m init --src ../carddemo/app --project "CardDemo" --owner "Demo owner" --agents claude \
  --target-stack "React + Spring Boot + DB2" > /dev/null

# Analysis: counts as reported in the walkthrough and README Results.
l2m analyze scan --src ../carddemo/app --out docs/analysis > /dev/null
python3 - docs/analysis/inventory.json <<'PY' && ok "scan: summary as published in docs/demo/README.md step 3" || fail=1
import json, sys
s = json.load(open(sys.argv[1]))["summary"]
want = {"programs": 46, "copybooks": 65, "jobs": 46, "screens": 21, "transactions": 25, "tables": 3,
        "unresolved": 0, "total_loc": 23018}
got = {k: s[k] for k in want}
if got != want:
    print(f"FAIL scan summary {got}, expected {want}"); sys.exit(1)
PY
l2m analyze slice --inventory docs/analysis/inventory.json --root CC00 CU01 > docs/analysis/slice.json
l2m map --inventory docs/analysis/inventory.json --programs COSGN00C COUSR01C > /dev/null

# Documents: the committed agent output, put through the deterministic document tools again.
rm -rf docs/requirements && cp -R "$OUT/requirements" docs/requirements
F=docs/requirements/user-admin/sign-on
l2m docs linkify "$F" > /dev/null
l2m docs trace "$F" --inject > /dev/null
l2m docs rtm sync "$F" > /dev/null
l2m docs rtm summary "$F" > /dev/null
l2m docs index docs/requirements > /dev/null

if [ "${L2M_UPDATE_DEMO:-}" = 1 ]; then
  cp docs/analysis/slice.json docs/analysis/target-mapping.md docs/analysis/data-mapping.md "$OUT/analysis/"
  rm -rf "$OUT/requirements" && cp -R docs/requirements "$OUT/requirements"
  echo "updated docs/demo/output; review the diff"
else
  for f in slice.json target-mapping.md data-mapping.md; do
    diff -u "$OUT/analysis/$f" "docs/analysis/$f" > "$W/$f.diff" && ok "analysis/$f unchanged" \
      || { cat "$W/$f.diff"; bad "analysis/$f drifted (L2M_UPDATE_DEMO=1 scripts/check-demo.sh to refresh after a deliberate change)"; }
  done
  diff -ru "$OUT/requirements" docs/requirements > "$W/req.diff" && ok "requirements unchanged by linkify, trace, rtm sync, rtm summary, index" \
    || { cat "$W/req.diff"; bad "requirements drifted (L2M_UPDATE_DEMO=1 scripts/check-demo.sh to refresh after a deliberate change)"; }
fi

if l2m docs validate "$F" > "$W/validate.txt"; then ok "docver.py validate"; else cat "$W/validate.txt"; bad "docver.py validate"; fi
if l2m docs check docs/requirements > "$W/check.txt"; then ok "docver.py check"; else cat "$W/check.txt"; bad "docver.py check"; fi

[ $fail = 0 ] && echo "demo output matches CardDemo at $CARDDEMO_SHA"
exit $fail
