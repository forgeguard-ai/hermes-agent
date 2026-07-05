# ForgeGuard fork documentation

Everything specific to the ForgeGuard fork of
[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
lives in this directory. Everything else in `docs/` and `website/docs/` is
upstream documentation and applies unchanged.

| Doc | What it covers |
| --- | --- |
| [`runtime-images.md`](runtime-images.md) | Pulling and running the fork's published images: a persistent server install from `runtime-*`, and a distrobox-based CLI install from `cli-*`. Tag scheme, required configuration, upgrades. |
| [`releases-and-versioning.md`](releases-and-versioning.md) | The `<upstream-base>-forgeguard.<n>` release scheme, what release-on-merge automation publishes, and how image tags map to releases. |
| [`upstream-sync-skill.md`](upstream-sync-skill.md) | The agent-agnostic runbook for syncing this fork to a new upstream release tag, including the fork-patch re-verification checklist. |
| [`code-review-instructions.md`](code-review-instructions.md) | Repo-specific context for running `/code-review` (local or cloud `ultra`): structure, conventions, risk hotspots, validation commands, fork guardrails, and how to use the Graphify map. Read before triggering a review. |
| [`graphify-refresh-skill.md`](graphify-refresh-skill.md) | Regenerate the Graphify codebase map with `scripts/graphify-refresh.sh` (code-only, no API key). Only `graphify-out/GRAPH_REPORT.md` is committed; the large `graph.json` is git-ignored and rebuilt locally. |

Related, outside this directory:

- The fork section at the top of the repo [`README.md`](../../README.md) — quickstarts.
- [`website/docs/user-guide/docker.md`](../../website/docs/user-guide/docker.md) — the upstream Docker reference; the `runtime-*` image behaves identically (substitute the image reference).
- `docs/agent-plans/` — checkbox-tracked work plans persisted by coding agents (fork policy; see `AGENTS.md`'s "ForgeGuard Fork" section).
- The fork PR policy and plan-saving rule — [`AGENTS.md`](../../AGENTS.md), "ForgeGuard Fork — Additions Below This Line".
