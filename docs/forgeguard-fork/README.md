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

Related, outside this directory:

- The fork section at the top of the repo [`README.md`](../../README.md) — quickstarts.
- [`website/docs/user-guide/docker.md`](../../website/docs/user-guide/docker.md) — the upstream Docker reference; the `runtime-*` image behaves identically (substitute the image reference).
- `docs/agent-plans/` — checkbox-tracked work plans persisted by coding agents (fork policy; see `AGENTS.md`'s "ForgeGuard Fork" section).
- The fork PR policy and plan-saving rule — [`AGENTS.md`](../../AGENTS.md), "ForgeGuard Fork — Additions Below This Line".
