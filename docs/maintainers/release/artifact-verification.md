# Artifact verification (ForgeGuard fork)

Maintainer checks for confirming that a published ForgeGuard artifact is the
build it claims to be. Pairs with the [Release process](./release-process.md).

## Runtime / CLI images

### Provenance by tag

Every image is published with an immutable `-<git-sha>` tag alongside the
`-<version>` and rolling `-latest` tags. The `-<git-sha>` traces the image back
to the exact commit it was built from:

```bash
docker pull ghcr.io/forgeguard-ai/hermes-agent:runtime-<git-sha>
docker inspect --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' \
  ghcr.io/forgeguard-ai/hermes-agent:runtime-<git-sha> 2>/dev/null || true
```

The `-<version>` and `-<git-sha>` tags for one release point at the same image
bytes as the tested build — the push step retags the exact tested image rather
than rebuilding.

### Variant and prebake labels

Both published targets carry ForgeGuard OCI labels. Confirm you have the intended
variant:

```bash
docker inspect \
  --format '{{ index .Config.Labels "com.forgeguard.hermes.variant" }} prebaked={{ index .Config.Labels "com.forgeguard.hermes.prebaked" }}' \
  ghcr.io/forgeguard-ai/hermes-agent:runtime-<release>
# expected: runtime prebaked=1   (or: cli prebaked=1)
```

### Runtime smoke check

```bash
docker run --rm ghcr.io/forgeguard-ai/hermes-agent:cli-<release> hermes --version
```

For the runtime image, start it with a dashboard and confirm health (see
[Runtime images](../../site/deployment/runtime-images.md)); the `HEALTHCHECK`
probes `/api/status` on port 9119.

## Desktop installers

Desktop artifacts are versioned only by the GitHub Release tag they are attached
to. A qualifying release must carry all five: `*.deb`, `*.AppImage`, `*.rpm`,
`*.dmg`, `*.zip`.

### macOS signature state

macOS builds are **ad-hoc signed, not notarized**. Confirm the ad-hoc signature
is present (a fully unsigned bundle is a regression — it shipped once, in
`v2026.7.1-forgeguard.1`, before the signing gate was added):

```bash
codesign --verify --deep --strict --verbose=2 /Applications/Hermes.app
codesign --display --verbose=2 /Applications/Hermes.app
```

Because the build is not notarized, `spctl --assess` will not pass — that is
expected for this fork, and the install-time workaround is
`xattr -cr /Applications/Hermes.app`.

### Linux installers

Linux `.deb`/`.rpm`/`.AppImage` are unsigned. Verify integrity by matching the
asset against the release rather than a signature.

## Release workflow step conclusions

The most important verification is that the release workflow actually did the
upload/push. Because reusable-workflow jobs report "success" even when a gated
step is skipped, confirm the **individual step** conclusions for the upload and
push steps in `release-on-merge.yml`'s called workflows — not just the job
conclusion. See the [Release process](./release-process.md#the-inputsupload--inputspush-gating-rule).

## Related

- [Release process](./release-process.md)
- [Image tags](../../site/reference/image-tags.md)
- [Desktop artifacts](../../site/deployment/desktop-artifacts.md)
