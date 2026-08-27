---
title: Distrobox / CLI image
description: The lean ForgeGuard Hermes CLI image for distrobox — retired in v0.20.7 and no longer built; reference for anyone still running a previously published cli-* tag.
order: 21
status: deprecated
---

# Distrobox / CLI image

:::warning Retired in v0.20.7

**`cli-*` images are no longer built or published.** Agent Command's distrobox
deployment kind is gone — `remote-docker` is the only deployment kind and it
runs `runtime-*` — so the target only cost a build slot on every release, and a
failing cli build blocked the entire release pipeline (that is exactly how
v0.20.7's first attempt died). The Dockerfile stage and the build-matrix entry
were removed with it.

Tags published before v0.20.7 (`cli-latest`, `cli-<version>`, `cli-<sha>`) are
untouched and still pull, but they are frozen at v0.20.6 and will not receive
fixes. For an interactive terminal, run the CLI inside the
[runtime image](./runtime-images.md) (`docker exec -it <container> hermes`), or
install Hermes on the host directly.

The rest of this page documents the retired image for anyone still running one.

:::

The `cli-*` image is a lean interactive build for **distrobox** (or plain
`docker run -it`): CLI, TUI, and browser tools, with no dashboard/gateway server
stack and no supervisor. Distrobox's host-integration package set and a
pre-generated `en_US.UTF-8` locale are pre-baked, so the first `distrobox enter`
is instant instead of running distrobox-init's usual multi-minute dependency
install.

Images are published to `ghcr.io/forgeguard-ai/hermes-agent`.

## Prerequisites

- A Linux host with [distrobox](https://distrobox.it/) and a container engine
  (Docker or Podman).
- Plain Docker also works for one-off CLI use (see below).

## Install via distrobox

Prefer an immutable `cli-<release>` tag for a stable environment; the example
uses `cli-latest` for convenience:

```bash
distrobox create --image ghcr.io/forgeguard-ai/hermes-agent:cli-latest --name hermes
distrobox enter hermes
hermes            # first run walks you through `hermes setup`
```

Notes:

- Your home directory is shared with the container (distrobox's default), so
  Hermes state lands in your own `~/.hermes` and survives container recreation
  and image upgrades.
- `hermes` is on `PATH` via a launcher shim; `/etc/profile.d/hermes.sh` exports
  the Playwright browser path and the lazy-install target for login shells.
- The install tree (`/opt/hermes`) is root-owned and read-only. Optional backends
  (messaging platforms, opt-in tool SDKs) are **not** baked in; Hermes
  lazy-installs them into `~/.hermes/lazy-packages` on first use — so, for
  example, `hermes gateway run` for Telegram works, it just fetches that adapter
  once.

## One-off use with plain Docker

```bash
docker run -it --rm \
  -v ~/.hermes:/root/.hermes \
  ghcr.io/forgeguard-ai/hermes-agent:cli-latest
```

## Verify

```bash
distrobox enter hermes -- hermes doctor
```

`hermes doctor` reports environment issues; a clean run confirms the CLI image
is wired up correctly.

## Upgrade

Recreate the box from a newer tag — your `~/.hermes` state is untouched:

```bash
distrobox rm hermes
distrobox create --image ghcr.io/forgeguard-ai/hermes-agent:cli-<newer-release> --name hermes
```

## Which variant do I want?

- Running a **persistent agent a client connects to** (Desktop Client Mode, web
  dashboard, messaging platforms, scheduled jobs)? Use the
  [runtime image](./runtime-images.md).
- Working **interactively in a terminal** on a Linux box and wanting host
  integration without installing the full dependency stack on the host? Use this
  `cli-*` image via distrobox.

## Related

- [Runtime images](./runtime-images.md)
- [Image tag families](../reference/image-tags.md)
- [Choose a ForgeGuard artifact](../getting-started/choose-a-forgeguard-artifact.md)
