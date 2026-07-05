# Code-Review Instructions (ForgeGuard fork)

Fork-specific context to feed Claude Code's `/code-review` so every review —
especially the billed cloud `/code-review ultra` — is grounded in this repo's
structure, conventions, and risk surface. Read this before triggering a review;
point the reviewer at it when scoping one.

This doc is a **review lens**, not a second copy of the contributor guide —
[`AGENTS.md`](../../AGENTS.md) is canonical. It links into AGENTS.md sections
rather than restating them.

> **Keep this current.** When structure, conventions, validation commands, or the
> Graphify workflow change, update this doc in the same change (see the ForgeGuard
> Fork section of [`AGENTS.md`](../../AGENTS.md)).

---

## 1. How the review is triggered

- **Local** — `/code-review [low|medium|high|xhigh|max]`. Low/medium: fewer,
  high-confidence findings; high→max: broader coverage, may include uncertain
  ones. Add `--comment` to post inline PR comments, or `--fix` to apply findings
  to the working tree.
- **Cloud** — `/code-review ultra` runs a deep multi-agent review of the current
  branch; `/code-review ultra <PR#>` reviews a GitHub PR. It is **user-triggered
  and billed** — the assistant cannot launch it; it needs a git repo and claude.ai
  auth. The cloud reviewer sees only **committed** state + the diff, so commit the
  refreshed `GRAPH_REPORT.md` (below) and anything you want reviewed first.

The reviewer loads `CLAUDE.md`/`AGENTS.md` and the docs they link (including this
one) during its scoping phase.

## 2. Project overview for the reviewer

Hermes is a self-improving AI agent (CLI + TUI + messaging gateway + desktop).
Primarily **Python**, with a TypeScript/Ink TUI, an Electron desktop app, and a
Docusaurus site. Canonical structure: [`AGENTS.md` → "Project Structure"](../../AGENTS.md)
and "What Hermes Is". Load-bearing entry points:

- `run_agent.py` — `AIAgent` core conversation loop; `model_tools.py` /
  `toolsets.py` — tool orchestration & discovery; `cli.py` — interactive CLI.
- `agent/` — provider adapters, memory, caching, compression.
- `gateway/` + `gateway/platforms/` — messaging gateway, one adapter per platform
  (telegram, discord, slack, whatsapp, signal, …).
- `tools/` (auto-discovered via `tools/registry.py`) + `tools/environments/` —
  terminal backends (local, docker, ssh, modal, daytona, singularity).
- `plugins/` — memory / model-providers / context_engine / kanban / observability
  / image_gen plugin trees.
- `skills/` + `optional-skills/` + curator (skill lifecycle); `cron/` (scheduler);
  kanban (multi-agent queue).
- `ui-tui/` (Ink/React TUI) + `tui_gateway/` (Python JSON-RPC backend);
  `acp_adapter/` (ACP server for VS Code/Zed/JetBrains); `apps/desktop/` (Electron).
- State/paths: `hermes_state.py` (SQLite + FTS5), `hermes_constants.py`
  (`get_hermes_home()` / `display_hermes_home()` — profile-aware paths).

## 3. Conventions the reviewer must enforce

Weigh diffs against AGENTS.md's own rules — flag violations:

- **Contribution rubric & Footprint Ladder** — reject scope-creep / redundant
  new capabilities per [`AGENTS.md` → "Contribution Rubric"](../../AGENTS.md) and
  "The Footprint Ladder". Prefer the smallest footprint that solves the problem.
- **Profile-safety** — never hardcode `~/.hermes`; use `get_hermes_home()` /
  `display_hermes_home()`. Code must be profile-safe (multi-instance). See
  "Profiles: Multi-Instance Support" and "DO NOT hardcode `~/.hermes` paths".
- **Tool handlers MUST return a JSON string** (registry contract, "Adding New
  Tools").
- **TypeScript** (desktop/TUI/website) — nanostores over prop-drilling, thin route
  roots, one-job hooks, interfaces for public props. See "TypeScript Style".
- **Known pitfalls** (treat any reintroduction as a finding): the gateway's TWO
  message guards must both bypass approval/control commands; `\033[K` in
  spinner/display code; new `simple_term_menu` usage; `_last_resolved_tool_names`
  process-global assumptions; hardcoded cross-tool references in schema
  descriptions. See "Known Pitfalls".

## 4. Repo-specific risk hotspots (weight these)

- **Prompt caching** — changes that reorder/mutate the system-prompt prefix break
  caching silently ("Prompt Caching Must Not Break").
- **Gateway** — dual message guards, background-process notifications, per-platform
  adapters; a change touching one platform shouldn't regress the shared path.
- **Secrets & config** — API keys live only in `~/.hermes/.env`; `config.yaml` for
  settings. Flag secrets read from the wrong loader or logged. See "Adding
  Configuration" (three config loaders — know which one you're in).
- **Terminal backends** (`tools/environments/`) — local/docker/ssh/modal/daytona
  isolation and cleanup semantics.
- **Dead code without E2E validation** and **squash-merges from stale branches**
  silently reverting fixes — both called out as recurring failure modes.

## 5. Validation the reviewer should expect

- **Tests** — `scripts/run_tests.sh` (**never bare `pytest`**; the wrapper enforces
  hermetic CI parity: blanked env, `TZ=UTC`, `LANG=C.UTF-8`, subprocess-per-file
  isolation). Scope with `scripts/run_tests.sh tests/<dir>/` or a single file.
- **Lint/type** — `ruff check .` (blocking in CI `lint.yml`) and `ty check`
  (both `uv tool install ruff` / `ty`). `scripts/lint_diff.py` produces the
  ruff+ty diff vs. the base ref used in PR summaries.
- **No change-detector tests** — reject tests that only assert model-catalog /
  config-version / enumeration snapshots. See "Don't write change-detector tests".
- **Tests must not write to `~/.hermes/`** — use `monkeypatch` / `tmp_path`.

A change lacking the validation its surface requires is itself a finding.

## 6. Fork guardrails the reviewer should respect

- **Never** propose opening a PR against `NousResearch/hermes-agent` — this fork
  merges to `ForgeGuard/hermes-agent:main` unless a human explicitly authorizes an
  upstream PR ("Fork PR Policy").
- Non-trivial multi-step work must have a saved plan under `docs/agent-plans/`
  ("Plan-Saving Rule").
- Upstream syncs follow [`upstream-sync-skill.md`](upstream-sync-skill.md).

## 7. Using Graphify to improve the review

A committed code map lives in `graphify-out/GRAPH_REPORT.md` (the ~49 MB
`graph.json` is git-ignored and regenerated locally — see
[`graphify-refresh-skill.md`](graphify-refresh-skill.md)). It's a **structural**
(Tree-sitter) graph — imports, definitions, call/containment edges — built with
**no API key or cost**.

**Before a review:**

1. `scripts/graphify-refresh.sh`, then commit `graphify-out/GRAPH_REPORT.md` so
   the cloud reviewer orients from an up-to-date overview.
2. Skim `GRAPH_REPORT.md` for whole-codebase structure.

**During local analysis** (CLI available; cloud reviews can't run it):

- `graphify affected "<changed symbol>"` — reverse traversal for **blast radius**
  (who breaks if this signature/return/exception changes). Most useful for
  correctness review in a 40k-node graph.
- `graphify path "<A>" "<B>"` / `graphify explain "<node>"` /
  `graphify query "<question>"` — targeted orientation instead of broad search.

Graphify **complements** the line-by-line diff review; it does not replace it.
Communities are numbered placeholders in the code-only graph; an optional semantic
pass (`graphify cluster-only . --no-viz --backend openai`, needs a key/credits)
names them.

## 8. Pre-review checklist

- [ ] `scripts/graphify-refresh.sh` run; `GRAPH_REPORT.md` committed.
- [ ] This doc reflects current structure/conventions/validation.
- [ ] Scope hints given when useful ("focus on `gateway/platforms/telegram`",
      "only `tools/environments/`").
- [ ] For a cloud review, everything to be reviewed is committed to the branch.
