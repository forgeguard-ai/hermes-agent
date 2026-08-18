---
title: Releases and upgrades
description: How ForgeGuard fork releases and image tags map to upstream, and how to upgrade and roll back ForgeGuard runtime deployments safely.
order: 32
status: stable
---

# Releases and upgrades

This page covers what a ForgeGuard release means for a **consumer** of the
artifacts — which tag to pin, how to upgrade, and how to roll back. The release
automation internals live in the maintainer documentation and are not needed to
operate a deployment.

## Release and version scheme

ForgeGuard releases are tagged with the Hermes Agent product version they ship,
for example `v0.20.3`:

- `v<hermes-version>` is the product version (semver, from `pyproject.toml`).
- If an already-released product version is re-cut — for example a fork-only
  fix lands before the next upstream sync — the re-cut gets a `-forgeguard.<n>`
  suffix instead of colliding on the tag: `v0.20.3-forgeguard.2`, counting the
  plain tag as cut 1.

Each release's notes also record the upstream `NousResearch/hermes-agent`
release this fork's `main` is synced to (the "Upstream release" line, from the
`FORK_UPSTREAM_BASE` marker at the repository root). See
[Compatibility](../fork/compatibility.md) for the current mapping.

> **History.** Releases up to `v2026.7.1-forgeguard.6` were named after the
> upstream base instead — date-shaped `<upstream-base>-forgeguard.<n>` tags.

## What is kept

Published artifacts are pruned on a retention policy, so history is **not**
unbounded. What you can rely on being downloadable:

| Artifact | Retained |
|---|---|
| GitHub Releases and their desktop installers | the **2 most recent** releases |
| `runtime-<version>` / `cli-<version>` images | the **newest** release's pair |
| `runtime-<git-sha>` / `cli-<git-sha>` images | the newest build's pair |
| `runtime-latest` / `cli-latest` images | always (rolling) |

Release **git tags** are kept even after their Release and installers are
pruned, so an older version can always be rebuilt from source at the exact
commit. If you need a specific older image to stay pullable, mirror it into your
own registry — do not rely on this one retaining it.
> Those tags remain valid; the product-version scheme applies from Hermes
> 0.19.0 onward.

## Image tags to use

| Tag | Mutability | Use |
|---|---|---|
| `runtime-<version>` / `cli-<version>` | immutable | Pin a deployment to a specific fork release. |
| `runtime-<git-sha>` / `cli-<git-sha>` | immutable | Trace an image back to its exact commit. |
| `runtime-latest` / `cli-latest` | rolling | Testing / always-newest; **drifts on every fork release**. |

For any durable deployment, pin an immutable `*-<version>` tag. The `*-latest`
tags are convenient for testing but are not immutable and move forward without
notice. See [Image tag families](../reference/image-tags.md) for full detail.

## Prerequisites

- A [runtime deployment](../deployment/runtime-images.md) with external state on
  `~/.hermes`.
- A [backup](./persistence-and-backups.md) of that state taken before upgrading.

## Upgrade

Because the image is immutable and state lives on the volume, upgrading is: pull
the new tag, remove the old container, recreate against the same state.

```bash
# 1. Back up first (see Persistence and backups).
# 2. Pull the target release.
docker pull ghcr.io/forgeguard-ai/hermes-agent:runtime-<new-release>

# 3. Recreate the container against the same ~/.hermes.
docker rm -f hermes
docker run -d --name hermes --restart unless-stopped \
  -v ~/.hermes:/opt/data -p 9119:9119 \
  -e HERMES_DASHBOARD=1 \
  -e HERMES_DASHBOARD_BASIC_AUTH_USERNAME=admin \
  -e HERMES_DASHBOARD_BASIC_AUTH_PASSWORD="<from your secret store>" \
  -e HERMES_DASHBOARD_BASIC_AUTH_SECRET="<stable secret>" \
  ghcr.io/forgeguard-ai/hermes-agent:runtime-<new-release> gateway run
```

## Verify

```bash
curl --fail http://localhost:9119/api/status
docker inspect --format '{{.State.Health.Status}}' hermes
```

The dashboard should return to `healthy` and your profiles/sessions should be
intact.

## Roll back

Rolling back is the same procedure with the previous release's tag — after
restoring the pre-upgrade [backup](./persistence-and-backups.md) if the newer
version migrated state in place. [What is kept](#what-is-kept) bounds how far
back you can go: the previous release's image is retained, but one older than
that may already have been pruned.

```bash
docker rm -f hermes
# (restore ~/.hermes from backup if needed)
docker run -d --name hermes --restart unless-stopped \
  -v ~/.hermes:/opt/data -p 9119:9119 \
  ghcr.io/forgeguard-ai/hermes-agent:runtime-<previous-release> gateway run
```

Read release notes before upgrading across an upstream base bump — a change in
the notes' "Upstream release" line can carry upstream behaviour changes that
affect state.

## macOS desktop installer note

Desktop `.dmg`/`.zip` builds are ad-hoc signed and not notarized; after
installing, run `xattr -cr /Applications/Hermes.app` once. See
[Desktop artifacts](../deployment/desktop-artifacts.md).

## Windows desktop installer note

The `-setup.exe` and `-portable.exe` builds are unsigned; SmartScreen shows
"Windows protected your PC" on first launch — **More info → Run anyway**. See
[Desktop artifacts](../deployment/desktop-artifacts.md#install-on-windows).

## Related

- [Image tag families](../reference/image-tags.md)
- [Persistence and backups](./persistence-and-backups.md)
- [Compatibility](../fork/compatibility.md)
