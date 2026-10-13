---
title: Desktop artifacts
description: Install the ForgeGuard-built Hermes Desktop app on Linux, macOS and Windows, including the macOS Gatekeeper workaround for ad-hoc-signed builds and the Windows SmartScreen step for unsigned ones.
order: 22
status: stable
---

# Desktop artifacts

ForgeGuard attaches prebuilt Hermes Desktop installers to every
[fork release](https://github.com/forgeguard-ai/hermes-agent/releases). They
package the same upstream Hermes Desktop app; ForgeGuard only builds and signs
the installers.

> **Signing state (version-sensitive).** macOS builds are **ad-hoc signed and
> not notarized** — this fork has no Apple Developer credentials. Linux builds
> are unsigned installers. Windows builds (from `v0.20.4`) are **unsigned** —
> no code-signing certificate on the fork — so SmartScreen warns on first
> launch. Verify the current state on the release you are installing; do not
> assume notarization or signing from older documentation.

## Available formats

| Platform | Formats | Notes |
|---|---|---|
| Linux | `.AppImage`, `.deb`, `.rpm` | Unsigned installers. |
| macOS | `.dmg`, `.zip` | Ad-hoc signed, not notarized. |
| Windows | `-setup.exe` (NSIS, per-user), `-portable.exe` | Unsigned; x64 only; SmartScreen "More info → Run anyway" on first launch. From `v0.20.4`. |

Desktop artifacts are versioned only by the GitHub Release tag they are attached
to (they do not carry the image `-<version>` tag scheme).

## Prerequisites

- A supported Linux distribution (for `.AppImage`/`.deb`/`.rpm`), macOS, or
  64-bit Windows 10/11 (for the `.exe` builds).
- Download the artifact for your platform from the
  [releases page](https://github.com/forgeguard-ai/hermes-agent/releases).

## Install on Linux

Use your distribution's installer for `.deb`/`.rpm`, or run the `.AppImage`
directly:

```bash
chmod +x Hermes-*.AppImage
./Hermes-*.AppImage
```

## Install on macOS

Because the build is ad-hoc signed and not notarized, macOS Gatekeeper
quarantines the downloaded `.dmg` and reports the app as "damaged". After copying
`Hermes.app` to `/Applications`, clear the quarantine attribute once:

```bash
xattr -cr /Applications/Hermes.app
```

Downloading the `.zip` with `curl -L` avoids the quarantine attribute entirely:

```bash
curl -L -o Hermes.zip "<release asset URL>"
unzip Hermes.zip
```

See [Troubleshooting](../troubleshooting/forgeguard-artifacts.md#macos-hermes-is-damaged-and-cant-be-opened)
for more detail.

## Install on Windows

Two builds are attached to each release, both unsigned and x64 only:

- `hermes-desktop-client-<version>-win-x64-setup.exe` — an NSIS installer that
  installs **per user** (no administrator prompt) and lets you choose the
  directory. It registers an uninstaller and a Start-menu shortcut.
- `hermes-desktop-client-<version>-win-x64-portable.exe` — a single executable
  that runs from wherever you save it; nothing is installed.

On first launch of either, Windows SmartScreen shows *"Windows protected your
PC"* because the binary carries no code-signing certificate. Click **More info
→ Run anyway**. The warning is per binary and stops once Microsoft has seen the
file enough times; it does not indicate a problem with the download. See
[Troubleshooting](../troubleshooting/forgeguard-artifacts.md#windows-windows-protected-your-pc)
for the details.

## Verify

Launch the app. To connect it to a persistent [runtime deployment](./runtime-images.md),
open the connection dialog, choose Client Mode, enter `http(s)://<host>:9119`,
and sign in with the [authentication provider](../operations/dashboard-authentication.md)
you configured on that deployment.

## Upstream desktop documentation

Usage of the desktop app itself — features, settings, Client Mode — is documented
upstream: [Desktop guide](https://hermes-agent.nousresearch.com/docs/user-guide/desktop).
This page covers only the ForgeGuard-built installers.

## Related

- [Runtime images](./runtime-images.md) — the deployment Client Mode connects to.
- [Troubleshooting ForgeGuard artifacts](../troubleshooting/forgeguard-artifacts.md)
- [ForgeGuard changes](../fork/forgeguard-changes.md)
