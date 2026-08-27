---
title: Choose a ForgeGuard artifact
description: Decide between the ForgeGuard runtime image and the desktop installers based on how you want to run Hermes.
order: 10
status: stable
---

# Choose a ForgeGuard artifact

ForgeGuard publishes three kinds of artifact from this fork. They all run the
same upstream Hermes Agent — they differ in how it is packaged and supervised.
Pick the one that matches how you want to run the agent.

## At a glance

| You want to… | Use | Why |
|---|---|---|
| Run a persistent agent that a client connects to (web dashboard, Desktop Client Mode, messaging platforms, scheduled jobs) | **Runtime image** (`runtime-*`) | Full supervised server: s6 keeps the dashboard and per-profile gateways running; state persists on a volume. |
| Work interactively in a terminal on a Linux workstation | **Runtime image**, then `docker exec -it <container> hermes` | The `cli-*` distrobox image was [retired in v0.20.7](../deployment/distrobox-cli.md); tags published before it still pull but are frozen at v0.20.6. |
| Run the graphical Hermes Desktop app on your own machine | **Desktop installers** | Native Linux (`.AppImage`/`.deb`/`.rpm`), macOS (`.dmg`/`.zip`) and Windows (`-setup.exe`/`-portable.exe`) builds attached to each fork release. |

## Prerequisites

- **Runtime image:** a container engine (Docker or Podman) and a host to run it
  on — a small VPS is enough. If you expose the dashboard beyond loopback you
  must configure [dashboard authentication](../operations/dashboard-authentication.md).
- **CLI image:** retired — see [Distrobox / CLI image](../deployment/distrobox-cli.md)
  if you are still running a tag published before v0.20.7.
- **Desktop installers:** a supported Linux distribution, macOS, or 64-bit
  Windows 10/11. See
  [Desktop artifacts](../deployment/desktop-artifacts.md) for formats and the
  macOS Gatekeeper note.

## Decision guide

1. **Is a client or a person going to connect to a long-running agent?**
   Use the [runtime image](../deployment/runtime-images.md). This is the
   shortest fork-specific path to a persistent Hermes deployment.

2. **Do you mainly want a terminal, on your own Linux box, that behaves like a
   local install but is containerised?**
   The [CLI image via distrobox](../deployment/distrobox-cli.md) filled this
   role until it was retired in v0.20.7. Run the runtime image and exec into it
   (`docker exec -it <container> hermes`), or install Hermes on the host.

3. **Do you want the desktop application?**
   Install a [desktop artifact](../deployment/desktop-artifacts.md). The desktop
   app can also connect to a runtime deployment through its Client Mode.

## Not sure you need a ForgeGuard artifact at all?

If you just want to install Hermes on your own machine the ordinary way, the
upstream native installer is the canonical path and is fully supported by Nous
Research:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

ForgeGuard's artifacts exist for the cases above — persistent container
deployments, containerised CLI use, and prebuilt desktop installers — not to
replace the upstream installer. See the upstream
[Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)
for the native path.

## Next steps

- [Runtime images](../deployment/runtime-images.md)
- [Distrobox / CLI image](../deployment/distrobox-cli.md)
- [Desktop artifacts](../deployment/desktop-artifacts.md)
- [Image tag families](../reference/image-tags.md)
