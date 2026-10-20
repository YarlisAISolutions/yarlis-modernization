#!/usr/bin/env bash
# Check what `npm publish` would ship: the dotfolders npm leaves out by default (.claude/skills, the .github kit)
# must be in, and caches, evals, tests and repo-only workflows must be out. Used by CI and the release job.
set -euo pipefail
cd "$(dirname "$0")/.."
files="$(npm pack --dry-run --json --ignore-scripts | node -e 'for (const f of JSON.parse(require("fs").readFileSync(0))[0].files) console.log(f.path)')"
fail=0
for need in bin/l2m.js lib/generate.js lib/python.js prompts/02-generate-brd.md AGENTS.md LICENSE README.md \
  .claude/skills/legacy-code-analysis/SKILL.md .claude/skills/legacy-code-analysis/scripts/inventory.py \
  .claude/skills/requirements-docs/SKILL.md .claude/skills/requirements-docs/scripts/docver.py \
  .claude/skills/requirements-docs/assets/templates/brd.md .claude/skills/mainframe-modernization/scripts/mapgen.py \
  .github/copilot-instructions.md .github/agents/requirements-analyst.agent.md .github/workflows/requirements-check.yml \
  .github/workflows/copilot-setup-steps.yml .github/pull_request_template.md; do
  grep -qxF "$need" <<< "$files" || { echo "missing from package: $need"; fail=1; }
done
if grep -E '__pycache__|\.pyc$|skill-evals|^tests/|^test/|^docs/|release\.yml|selftest\.yml' <<< "$files"; then
  echo "unexpected files in package (above)"; fail=1
fi
[ $fail = 0 ] && echo "package contents ok ($(wc -l <<< "$files" | tr -d ' ') files)"
exit $fail
