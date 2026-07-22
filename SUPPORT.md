# Support

This repository is a **ForgeGuard maintained fork** of
[`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent).
Nous Research owns and maintains the Hermes product; ForgeGuard maintains a
distribution overlay (runtime and CLI container images, desktop installers, and
the release/versioning scheme). Where you file an issue depends on which of those
it concerns.

## Where to file

| Your issue is about… | File it at |
|---|---|
| A ForgeGuard **runtime or CLI image** (GHCR), its container packaging, or ForgeGuard-only container behaviour | [`forgeguard-ai/hermes-agent`](https://github.com/forgeguard-ai/hermes-agent/issues) |
| A ForgeGuard **desktop installer** (`.AppImage`/`.deb`/`.rpm`/`.dmg`/`.zip`) or its signing state | [`forgeguard-ai/hermes-agent`](https://github.com/forgeguard-ai/hermes-agent/issues) |
| The **release / version tag scheme** or a missing/incorrect release artifact | [`forgeguard-ai/hermes-agent`](https://github.com/forgeguard-ai/hermes-agent/issues) |
| **Hermes itself** — agent behaviour, providers, tools, the messaging gateway, skills, memory, or the desktop app's features | [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent/issues) |
| A security vulnerability | See [SECURITY.md](./SECURITY.md) — do not open a public issue |

## Reproduce on upstream first

If a problem is not obviously specific to a ForgeGuard artifact, **reproduce it
on an upstream install first**:

- If it reproduces on an upstream native install or the upstream Docker image,
  it is a **Hermes** issue → file it upstream at
  [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent/issues).
- If it only happens with a ForgeGuard artifact, it is a **ForgeGuard** issue →
  file it at [`forgeguard-ai/hermes-agent`](https://github.com/forgeguard-ai/hermes-agent/issues).

This keeps upstream's issue tracker free of packaging-specific reports and gets
your issue to the people who can act on it fastest.

## What to include

For a ForgeGuard artifact issue, include:

- The exact artifact and tag (e.g. `runtime-v0.19.0`, or the
  desktop installer filename and release tag).
- The Hermes product version (from the release notes or `hermes --version`).
- Your platform and container engine (for images) or OS (for desktop).
- Whether the problem reproduces on an upstream install.

## Support expectations

ForgeGuard maintains the distribution artifacts on a best-effort basis and makes
no private-support commitment. **Nous Research does not provide support for
ForgeGuard-specific builds.** For general questions about using Hermes, see the
upstream [documentation](https://hermes-agent.nousresearch.com/docs/) and
community channels.

See also: [ForgeGuard documentation](./docs/site/index.md) ·
[How ForgeGuard relates to upstream](./docs/site/fork/upstream.md).
