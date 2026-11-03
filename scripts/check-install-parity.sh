#!/usr/bin/env bash
# Both install paths must install the same files with the same content: `l2m init` (lib/install.js) and the bash
# fallback of scripts/install.sh (L2M_BASH=1), each with every agent. Only `l2m init` writes l2m.config.json and
# docs/requirements/PROJECT-CONTEXT.md (the bash path tells you to run docver.py init), so those two are left out.
# Usage: bash scripts/check-install-parity.sh   (needs Node 22+, python3 and git; writes only to a temp dir)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
mkdir "$W/node" "$W/bash"
node "$ROOT/bin/l2m.js" init "$W/node" > /dev/null
L2M_BASH=1 bash "$ROOT/scripts/install.sh" "$W/bash" > /dev/null
rm "$W/node/l2m.config.json" "$W/node/docs/requirements/PROJECT-CONTEXT.md"
if ! diff -r "$W/node" "$W/bash"; then
  echo "FAIL install paths differ (< l2m init, > scripts/install.sh): change lib/install.js and scripts/install.sh together"
  exit 1
fi
echo "install paths ok ($(find "$W/node" -type f | wc -l | tr -d ' ') files, same content)"
