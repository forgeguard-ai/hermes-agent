#!/usr/bin/env bash
# Refresh the ForgeGuard fork's Graphify codebase map.
#
# Rebuilds graphify-out/graph.json + GRAPH_REPORT.md from the current tree using
# pure Tree-sitter (AST) extraction — no LLM, no API key, nothing leaves the host.
# The corpus stays code-only because .graphifyignore excludes doc/markup formats
# that would otherwise demand a semantic (LLM) backend.
#
# Only GRAPH_REPORT.md is tracked in git (see .gitignore); the ~49MB graph.json is
# regenerated locally for `graphify query`/`affected` and read by cloud reviews via
# the report. Run this before a code review; commit the refreshed GRAPH_REPORT.md.
#
# Usage:
#   scripts/graphify-refresh.sh            # incremental refresh (fast)
#   scripts/graphify-refresh.sh --force    # overwrite even if the rebuild has fewer nodes
#
# See docs/forgeguard-fork/graphify-refresh-skill.md for the full runbook and the
# optional semantic (OpenAI) upgrade.

set -euo pipefail

# Repo root = parent of this script's directory.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v graphify >/dev/null 2>&1; then
  # uv installs to ~/.local/bin, which is not always on a non-login PATH.
  export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v graphify >/dev/null 2>&1; then
  cat >&2 <<'EOF'
graphify not found. Install it (Python tool; PyPI package is `graphifyy`):

  curl -LsSf https://astral.sh/uv/install.sh | sh   # if uv is missing
  uv tool install graphifyy

Then re-run scripts/graphify-refresh.sh. If it is still not found, add
~/.local/bin to PATH or run `uv tool update-shell` and open a new terminal.
EOF
  exit 1
fi

echo "[graphify-refresh] rebuilding code map in $ROOT (code-only, no API key)..."
graphify update . "$@"

echo
echo "[graphify-refresh] done. Commit the tracked report:"
echo "    git add graphify-out/GRAPH_REPORT.md && git commit -m 'chore: refresh graphify map'"
