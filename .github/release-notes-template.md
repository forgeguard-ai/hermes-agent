__ORIGIN__

**Hermes Agent version:** v__HERMES_VERSION__
**Upstream release:** [__BASE_TAG__](https://github.com/NousResearch/hermes-agent/releases/tag/__BASE_TAG__)__UPSTREAM_COMMIT__

Tracks upstream base `__BASE_TAG__`. See `docs/site/` for the fork's
image guide, versioning scheme, and how this fork stays current with
[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).

### Docker

```bash
# Full supervised server image (dashboard + gateways):
docker pull __IMAGE__:runtime-__VERSION__
# Rolling tag: runtime-latest
```

**Runtime image digest:** __RUNTIME_DIGEST__

> [!IMPORTANT]
> **Remote deployments need an auth provider as of `v2026.7.1`.** Upstream's
> June-2026 hardening means a gateway bound to a non-loopback address (the
> container binds `0.0.0.0`) now **refuses to start** unless an auth provider
> is configured — `HERMES_DASHBOARD_INSECURE` / `--insecure` and static-token
> mode no longer open a public dashboard. Set one of:
> - **Password:** `HERMES_DASHBOARD_BASIC_AUTH_USERNAME` + `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD`
> - **OAuth:** `HERMES_DASHBOARD_OAUTH_CLIENT_ID`
>
> If the desktop client can't reach an upgraded deployment, check the container
> log for `Refusing to bind dashboard to 0.0.0.0` — that means no provider is
> set. The desktop connection dialog signs in against either provider.

### Desktop installers

Linux (`.AppImage`, `.deb`, `.rpm`), macOS (`.dmg`, `.zip`) and Windows
(`-setup.exe` installer, `-portable.exe`) installers are attached below. None
is signed with a paid certificate (no Apple Developer or Windows code-signing
credentials on this fork); the macOS build is ad-hoc signed, the Windows
builds are unsigned.

**Linux:** no extra step.

**Windows:** SmartScreen shows *"Windows protected your PC"* on first launch of
an unsigned binary — click **More info → Run anyway**. The `-setup.exe` installs
per-user (no administrator prompt); the `-portable.exe` runs from wherever it is
saved. x64 only.

**macOS:** because the app isn't notarized, Gatekeeper quarantines it on
download and shows *"Hermes is damaged and can't be opened"* — right-click →
Open does **not** clear this. After copying Hermes.app to /Applications, strip
the quarantine flag once:

```bash
xattr -cr /Applications/Hermes.app
```

Then open it normally. (Alternatively, download the `.zip` with
`curl -L -o hermes.zip <asset-url>` — a curl download never sets the
quarantine attribute, so no `xattr` step is needed.)
