# Hermes Agent — Dev Container

A ready-to-code environment for hacking on Hermes Agent, usable with
VS Code Dev Containers or GitHub Codespaces.

## What you get

- **Python 3.13** (matches the production runtime and `[tool.ty.environment]`).
- **uv** — the project's package manager, preinstalled.
- **Node 22 LTS** — for browser tools, the Ink TUI (`ui-tui/`), and the
  dashboard/desktop frontends.
- **System deps**: `ripgrep` (backs `search_files`), `ffmpeg`, and the build
  toolchain (`cmake`, `libffi-dev`, `libolm-dev`) needed for native source
  builds like Matrix's `python-olm`.
- A project-local **`.venv`** with `hermes-agent[all,dev]` installed editable.
- A persisted **`$HERMES_HOME`** (`/home/vscode/.hermes`) seeded with
  `config.yaml`, the standard dirs, and an empty `.env`.

Both `.venv` and `$HERMES_HOME` live on named volumes, so a container rebuild
keeps your installed deps, sessions, skills, and keys.

## First run

The container creates the venv and installs dependencies automatically
(`post-create.sh`). Once it finishes:

```bash
source .venv/bin/activate

# Add at least one LLM provider key (secrets only ever go in .env):
echo "OPENROUTER_API_KEY=..." >> "$HERMES_HOME/.env"

hermes doctor          # diagnostics
hermes chat -q "Hello" # smoke test
scripts/run_tests.sh   # CI-parity test suite
```

## Notes

- This is a **development** container — it bind-mounts the repo and installs
  editable. It is intentionally distinct from the root `Dockerfile`, which
  builds the sealed, s6-supervised production image.
- The dashboard port (`9119`) is forwarded. Run `hermes dashboard` and open
  the forwarded URL; keep it bound to localhost unless you understand the
  auth implications.
- `[all,dev]` excludes opt-in backends (messaging, matrix, voice, …). Those
  lazy-install at first use, or add them explicitly:
  `uv pip install -e ".[messaging]"`.
