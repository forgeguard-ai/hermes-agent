# Graphify Refresh Skill (ForgeGuard fork)

An agent-agnostic runbook for regenerating this fork's [Graphify](https://graphify.net)
codebase map so it matches the current tree. Works the same whether you're
Cursor, GitHub Copilot, Codex, or Claude Code — it's a shell wrapper around the
`graphify` CLI, no tool-specific features required.

Run it **before a code review** (local or the cloud `/code-review ultra`), or
whenever the code has drifted from the committed map. This skill *produces/updates*
the graph; [`code-review-instructions.md`](code-review-instructions.md) describes
how a reviewer *uses* it.

## What gets tracked (and why only the report)

Graphify writes to `graphify-out/`. For this repo the graph is large
(~40k nodes / ~49 MB `graph.json`), so **only the small human-readable
`GRAPH_REPORT.md` (~290 KB) is committed** (see `.gitignore`). That report is what
the cloud reviewer reads for orientation. The heavy `graph.json` is git-ignored
and regenerated locally — the cloud reviewer can't run the CLI anyway, and a
local rebuild is ~1 minute with no API key.

## Prerequisites

- Python tool `graphify` (PyPI package `graphifyy`). Install once if missing:

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh   # if uv is missing
  uv tool install graphifyy
  ```

  `uv` installs to `~/.local/bin`; if `graphify: command not found`, add that to
  `PATH` or run `uv tool update-shell` and open a new terminal.

## Refresh (code-only, no API key, no cost)

```bash
scripts/graphify-refresh.sh          # incremental; rebuilds graph.json + GRAPH_REPORT.md
scripts/graphify-refresh.sh --force  # if a refactor deleted code and node count dropped
```

The wrapper runs `graphify update .` — pure Tree-sitter (AST) extraction, nothing
leaves the host. It auto-skips the HTML visualization (the graph exceeds
Graphify's 5000-node viz limit). The corpus stays code-only because
`.graphifyignore` excludes doc/markup formats (`*.md`, `*.yaml`, `*.html`, `docs/`,
`website/`, `tests/`, …) that would otherwise demand an LLM key. **Don't remove
those excludes** unless you're deliberately switching to a semantic backend.

## Commit the tracked report

```bash
git add graphify-out/GRAPH_REPORT.md
git commit -m "chore: refresh graphify codebase map"
```

## (Optional) Semantic upgrade — readable community names

The code-only report labels clusters `Community N`. To get human-readable names
plus LLM-inferred cross-file links (costs API tokens; sends code to the provider),
set a key and re-cluster. OpenAI example:

```bash
export OPENAI_API_KEY=<key>
graphify cluster-only . --no-viz --backend openai
```

Optional enrichment, never required for a valid refresh.

## Completion criteria

- `scripts/graphify-refresh.sh` succeeded; `GRAPH_REPORT.md` regenerated. Its
  "Built from commit" line names the commit the graph was built against — for a
  committed report this necessarily lags `HEAD` (the report is regenerated, then
  committed on top), so verify it is an ancestor of `HEAD`
  (`git merge-base --is-ancestor <sha> HEAD`) or matches the pre-commit `HEAD`,
  rather than exact-matching `git rev-parse HEAD`.
- The corpus stayed code-only: the report's `## Corpus Check` section is present
  and its `Token cost:` line reads `0 input · 0 output` (pure AST extraction, no
  API key required).
- `graphify-out/GRAPH_REPORT.md` is staged/committed; `graph.json` and the other
  internals remain git-ignored.
- A sanity query works locally, e.g. `graphify query "<subsystem you changed>"` or
  `graphify affected "<changed symbol>"`.
