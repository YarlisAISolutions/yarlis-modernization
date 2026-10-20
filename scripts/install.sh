#!/usr/bin/env bash
# Install the requirements toolkit into another repository so every developer, with Copilot or Claude Code,
# produces the same per-feature BRD/FRD/SRD/RTM documents.
#
#   scripts/install.sh <target-repo> [--force] [--dry-run]
#
# Copies: .claude/skills/{legacy-code-analysis,requirements-docs,mainframe-modernization}, the Copilot files
# (.github/copilot-instructions.md, instructions/, prompts/, agents/), the CI workflow, PR template, issue form,
# AGENTS.md, prompts/, and creates docs/requirements/. Existing files are never overwritten without --force;
# for copilot-instructions.md and AGENTS.md an existing file gets a marked section appended instead.
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-}"; shift || true
FORCE=0; DRY=0
for a in "$@"; do
  case "$a" in --force) FORCE=1 ;; --dry-run) DRY=1 ;; *) echo "unknown option $a"; exit 2 ;; esac
done
[ -n "$TARGET" ] && [ -d "$TARGET" ] || { echo "usage: $0 <target-repo> [--force] [--dry-run]"; exit 2; }
TARGET="$(cd "$TARGET" && pwd)"
[ "$TARGET" != "$SRC" ] || { echo "target is this repository"; exit 2; }

run() { if [ $DRY = 1 ]; then echo "would: $*"; else "$@"; fi; }

copy() {  # copy <relative path> [destination relative path]
  local rel="$1" dst="${2:-$1}"
  if [ -e "$TARGET/$dst" ] && [ $FORCE = 0 ]; then echo "keep     $dst (exists; --force to replace)"; return; fi
  run mkdir -p "$(dirname "$TARGET/$dst")"
  run cp -R "$SRC/$rel" "$TARGET/$dst"
  echo "add      $dst"
}

append_section() {  # append_section <relative path>: add our content once, between markers
  local rel="$1" begin="<!-- yarlis-modernization:begin -->" end="<!-- yarlis-modernization:end -->"
  if [ ! -e "$TARGET/$rel" ]; then copy "$rel"; return; fi
  if grep -qF "$begin" "$TARGET/$rel"; then echo "keep     $rel (section already present)"; return; fi
  if [ $DRY = 1 ]; then echo "would: append section to $rel"; return; fi
  { printf '\n%s\n' "$begin"; cat "$SRC/$rel"; printf '%s\n' "$end"; } >> "$TARGET/$rel"
  echo "append   $rel"
}

for s in legacy-code-analysis requirements-docs mainframe-modernization; do
  if [ -e "$TARGET/.claude/skills/$s" ] && [ $FORCE = 1 ]; then run rm -rf "$TARGET/.claude/skills/$s"; fi
  copy ".claude/skills/$s"
done

append_section ".github/copilot-instructions.md"
append_section "AGENTS.md"
for f in instructions/requirements-docs.instructions.md instructions/legacy-analysis.instructions.md \
         prompts/new-feature-requirements.prompt.md prompts/analyze-legacy.prompt.md \
         prompts/change-request.prompt.md prompts/assess-implementation.prompt.md \
         agents/requirements-analyst.agent.md workflows/requirements-check.yml \
         ISSUE_TEMPLATE/feature-requirements.yml; do
  copy ".github/$f"
done
copy ".github/pull_request_template.md"
if [ -e "$TARGET/.github/workflows/copilot-setup-steps.yml" ] && [ $FORCE = 0 ]; then
  echo "keep     .github/workflows/copilot-setup-steps.yml (exists: add Python 3 setup and fetch-depth: 0 to it by hand)"
else
  copy ".github/workflows/copilot-setup-steps.yml"
fi
copy "prompts"
run mkdir -p "$TARGET/docs/requirements"

cat <<EOF

Done. Next steps in $TARGET:
  1. python3 .claude/skills/requirements-docs/scripts/docver.py init --type context --dir docs/requirements --project "<Name>" --src <legacy-source>
  2. Fill docs/requirements/PROJECT-CONTEXT.md (owner, users, constraints; Unknown where unknown)
  3. Optional: add CODEOWNERS lines, e.g.  docs/requirements/accounts/  @org/accounts-owners
  4. In Copilot Chat or Claude Code: /new-feature-requirements module=<m> feature=<f> scope=<...>
  5. Commit on a branch and open a PR: CI runs docver.py check and bumpcheck
EOF
