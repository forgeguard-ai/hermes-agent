---
title: Image tags
description: Reference for the ForgeGuard runtime and CLI image tag families on GHCR, their mutability, and how they map to fork releases.
order: 40
status: stable
---

# Image tags

ForgeGuard publishes two image variants to `ghcr.io/forgeguard-ai/hermes-agent`
from one multi-target `Dockerfile`. Each variant carries three tag families.

## Variants

| Variant | What it is |
|---|---|
| `runtime-*` | Full supervised server image (s6-overlay, dashboard, per-profile gateways, browser + messaging/Matrix adapters). See [Runtime images](../deployment/runtime-images.md). |
| `cli-*` | **Retired in v0.20.7 — no longer built.** Was a lean interactive image for distrobox / one-off CLI use. Tags published earlier still pull but are frozen at v0.20.6. See [Distrobox / CLI image](../deployment/distrobox-cli.md). |

The published target carries the OCI labels
`com.forgeguard.hermes.prebaked=1` and
`com.forgeguard.hermes.variant=runtime` (retired `cli-*` images carry
`variant=cli`).

## Tag families

| Tag pattern | Mutability | Meaning |
|---|---|---|
| `runtime-<version>` | immutable | A specific fork release, e.g. `runtime-v0.20.4`. Pin durable deployments here. |
| `runtime-<git-sha>` | immutable | The exact commit an image was built from; use to trace provenance. |
| `runtime-latest` | rolling | The newest published build. Convenient for testing; **moves on every fork release** and is not immutable. |

The `-<version>` tags exist only for releases where the release automation
supplies a version; the `-<git-sha>` and `-latest` tags are always published.
`<version>` is the fork release tag — the Hermes product version
(`v<hermes-version>`, e.g. `v0.20.4`) since Hermes 0.19.0, gaining a
`-forgeguard.<n>` suffix only when an already-released product version is
re-cut; images for releases up to `v2026.7.1-forgeguard.6` carry older
date-shaped `<upstream-base>-forgeguard.<n>` tags. See
[Releases and upgrades](../operations/releases-and-upgrades.md).

## Choosing a tag

- **Production / anything you care about:** an immutable `*-<version>` tag.
- **Provenance / debugging a specific build:** the `*-<git-sha>` tag.
- **Testing the newest build:** `*-latest`, understanding it will drift.

## Inspecting an image

Confirm a pulled image's variant and provenance from its labels:

```bash
docker inspect \
  --format '{{ index .Config.Labels "com.forgeguard.hermes.variant" }}' \
  ghcr.io/forgeguard-ai/hermes-agent:runtime-<release>
```

## Related

- [Releases and upgrades](../operations/releases-and-upgrades.md)
- [Compatibility](../fork/compatibility.md)
- [Runtime images](../deployment/runtime-images.md)
