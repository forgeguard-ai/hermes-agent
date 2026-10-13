#!/usr/bin/env bash
# Dev container bootstrap for Hermes Agent. Runs once on container creation
# (onCreateCommand). Creates the project venv, installs Python + Node deps,
# and seeds a writable $HERMES_HOME so `hermes` works out of the box.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

echo "▶ Fixing ownership of mounted volumes (.venv + \$HERMES_HOME)..."
# Named volumes mount root-owned; hand them to the unprivileged dev user so
# uv/npm/hermes can write to them. The vscode user has passwordless sudo.
sudo chown -R "$(id -u):$(id -g)" "$REPO_ROOT/.venv" "$HERMES_HOME" 2>/dev/null || true

echo "▶ Creating virtualenv (.venv, Python 3.13)..."
uv venv .venv --python 3.13

echo "▶ Installing hermes-agent with [all,dev] extras..."
# uv auto-discovers ./.venv as the install target.
uv pip install -e ".[all,dev]"

echo "▶ Installing Node workspace deps (browser tools, TUI, dashboard)..."
# Non-fatal: a network hiccup here shouldn't block Python development.
npm install --prefer-offline --no-audit || \
    echo "  ⚠ npm install failed — rerun manually if you need browser/TUI tools."

echo "▶ Seeding \$HERMES_HOME ($HERMES_HOME)..."
mkdir -p "$HERMES_HOME"/{cron,sessions,logs,memories,skills}
if [ ! -f "$HERMES_HOME/config.yaml" ] && [ -f cli-config.yaml.example ]; then
    cp cli-config.yaml.example "$HERMES_HOME/config.yaml"
fi
touch "$HERMES_HOME/.env"

cat <<'EOF'

✅ Dev container ready.

   Activate the venv:   source .venv/bin/activate
   Add a provider key:  echo "OPENROUTER_API_KEY=..." >> "$HERMES_HOME/.env"
   Smoke test:          hermes doctor
   Run the test suite:  scripts/run_tests.sh

EOF
