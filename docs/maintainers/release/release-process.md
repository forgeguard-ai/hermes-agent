# Release process (ForgeGuard fork)

Maintainer reference for how ForgeGuard fork releases are computed and published.
This is the CI-internals companion to the user-facing
[Releases and upgrades](../../site/operations/releases-and-upgrades.md) page —
consumers do not need anything here.

`AGENTS.md` (its "ForgeGuard Fork" section) remains canonical for fork policy;
this doc describes the release automation specifically.

## Version scheme

Since Hermes 0.19.0, fork releases are tagged with the Hermes Agent product
semver, e.g. `v0.19.0`:

- `<hermes-version>` is read from `pyproject.toml` by `compute-version` —
  aligning fork releases with ForgeGuard project versioning conventions.
- **Since `v0.20.4` the fork version is its own line.** It started equal to the
  Hermes product version and bumps the patch number by one on *every* fork
  release — an upstream sync, a fork-only fix, or both in one PR — so the tag
  sequence stays strictly increasing and unambiguous (`v0.20.3` was a fork-only
  cut; upstream's `v2026.8.16.2` is *also* product `0.20.3`, and following the
  old rule would have collided into `v0.20.3-forgeguard.2`). Consequences:
  `pyproject.toml`, `hermes_cli/__init__.py`, `uv.lock`, `apps/desktop/package.json`
  and the desktop entry in `package-lock.json` are **hand-set** to the fork
  version at every release (a sync no longer takes them upstream byte-identical);
  the upstream product version is recorded by `FORK_UPSTREAM_BASE` and the
  release notes' "Upstream release" line, and the mapping lives in
  `docs/site/fork/compatibility.md`.
- The `-forgeguard.<n>` re-cut suffix remains as the workflow's safety net if a
  version is ever released twice; under the rule above it should not fire.

The upstream base tag no longer names the release. It is still read from the
`FORK_UPSTREAM_BASE` marker file at the repo root — which the
[upstream-sync runbook](../upstream-sync/sync-policy.md) rewrites on every sync —
but now only feeds the "Upstream release" traceability line in the release
notes. The marker must still always be present and correct: if it is missing,
`compute-version` falls back to `git describe --tags --abbrev=0`, which can pick
an unrelated or stale tag.

Releases up to `v2026.7.1-forgeguard.6` used the old date-shaped
`<upstream-base>-forgeguard.<n>` scheme and keep those tags.

## What gets published, and when

`release-on-merge.yml` runs when a PR **merges into `main`** and the change is
release-relevant. It skips (no release, no builds) when the PR carries the
`no-release` label or touches no release-relevant paths — the path gate excludes
`docs/*`, `website/*`, `tests/*`, `.github/*`, and `*.md`, so docs-only and
CI-only merges don't produce releases. For qualifying merges it:

1. Computes the release version (`compute-version` job): the product semver
   from `pyproject.toml` (e.g. `v0.19.0`), with a `-forgeguard.<n>` suffix only
   on a re-cut; `FORK_UPSTREAM_BASE` feeds only the release-notes traceability
   line.
2. Calls `build-desktop-client.yml` with `upload: true` → unsigned Linux
   installers (`.AppImage`, `.deb`, `.rpm`), ad-hoc-signed macOS installers
   (`.dmg`, `.zip`) and unsigned Windows installers (`-setup.exe`,
   `-portable.exe`). It does **not** pass a `version:` input; desktop artifacts
   are versioned only by the Release tag.
3. Calls `build-runtime-images.yml` with `push: true` and
   `version: <computed version>` → builds, tests, and pushes the runtime image
   to `ghcr.io/forgeguard-ai/hermes-agent` with tags `runtime-<sha>` /
   `runtime-latest` / `runtime-<version>` (the `cli-*` image family was
   retired in fork v0.20.7).
4. Publishes a GitHub Release with the installers attached and the image pull
   commands in the notes.

Those two build workflows have no triggers of their own besides `workflow_call`
and `workflow_dispatch` (the manual escape hatch — e.g. validating a branch's
images with `push=false`); `release-on-merge.yml` is the single merge-time
builder. A `push:` trigger on either build workflow would reintroduce double
builds on qualifying merges — do not add one.

## The `inputs.upload` / `inputs.push` gating rule

In both `build-desktop-client.yml`'s upload steps and
`build-runtime-images.yml`'s push step, the `if:` gates on `inputs.upload` /
`inputs.push` **directly**. Do **not** gate on
`github.event_name == 'workflow_call'`: inside a reusable workflow,
`github.event_name` is always the *caller's* triggering event (e.g.
`pull_request` for `release-on-merge.yml`), never literally `"workflow_call"`.
That exact regression silently skipped every installer upload and image push for
two releases before it was caught (2026-07-02) — the jobs report "success"
either way, so it only surfaces by checking **individual step** conclusions, not
the job conclusion. Re-verify this after every upstream sync (see the
[patch inventory](../upstream-sync/patch-inventory.md)).

## Image tag families

| Tag | Mutability | Use |
| --- | --- | --- |
| `runtime-<version>` | immutable | pin deployments to a specific fork release |
| `runtime-<git-sha>` | immutable | trace any image back to its exact commit |
| `runtime-latest` | rolling | testing / always-newest |

See [Image tags](../../site/reference/image-tags.md) for the consumer-facing
description of the image and how to run it.

## macOS installer signing

The fork has no Apple Developer credentials, so macOS builds are ad-hoc signed
(NOT notarized). `scripts/notarize.cjs` no-ops without Apple API-key env vars;
`scripts/after-pack.cjs` performs ad-hoc signing. The build sets
`CSC_FOR_PULL_REQUEST: "true"` so ad-hoc signing runs even though the reusable
workflow is invoked from a `pull_request` event, and a `codesign --verify` gate
fails the build if the bundle regresses to unsigned. Gatekeeper still quarantines
the downloaded `.dmg` as "damaged"; after copying to `/Applications` run once:

```bash
xattr -cr /Applications/Hermes.app
```

(Downloading the `.zip` with `curl -L` avoids the quarantine attribute entirely.)

## Verifying a release

After a merge that should release, confirm:

- `release-on-merge.yml` fired, completed fully green, and — checking individual
  **step** conclusions — actually uploaded installers and pushed both runtime
  images rather than silently skipping.
- The GitHub Release is tagged with the product semver (plus the `-forgeguard.<n>`
  re-cut suffix when that version had already released), its notes carry the
  expected "Upstream release" line, and it has all seven installers attached
  (`*.deb`, `*.AppImage`, `*.rpm`, `*.dmg`, `*.zip`, `*-setup.exe`,
  `*-portable.exe`).

See [Artifact verification](./artifact-verification.md) for provenance checks on
the published images and installers.

## Retention

Published artifacts are pruned by
[`artifact-retention.yml`](../../../.github/workflows/artifact-retention.yml)
(`workflow_dispatch` only; `dry_run` defaults to true). Its policy:

| Artifact | Retained |
|---|---|
| GitHub Releases + installers | newest 2 (`keep_releases`) |
| `runtime-<version>` images | newest 2 releases (`keep_builds`) |
| `runtime-<git-sha>` images | the same 2 builds |
| `runtime-latest` / `cli-latest` | always |
| `buildcache-runtime-amd64` / `buildcache-cli-amd64` | always |
| Untagged GHCR versions | always (they back the buildcache index) |
| `hermes-desktop-linux` / `-macos` / `-windows` artifacts | newest 1 each |
| Every other workflow artifact | dropped once older than `min_age_hours` (24 h) |

`keep_builds` equals `keep_releases` on purpose: the roll-back path in
[Releases and upgrades](../../site/operations/releases-and-upgrades.md#roll-back)
promises the *previous* release's image is still pullable, and a
`keep_builds` of 1 would break that promise the moment a release is cut. The
24 h floor on workflow artifacts exists because `review-status-*`,
`test-durations-slice-*` and the desktop uploads are read by `workflow_run`
consumers minutes after upload — a prune dispatched mid-CI must not race them.

**Release git tags are never pruned** — only the Release object and its uploaded
installers. Every version therefore stays rebuildable from source at its exact
commit, which is what makes the retention window safe to keep this tight.

Two things to know before running it:

- The script refuses to apply a **partial** plan. If it cannot read one scope
  (a packages `403` is the usual cause — set `GHCR_CLEANUP_TOKEN` to a PAT with
  `read:packages` + `delete:packages`), it aborts rather than pruning releases
  while silently leaving images behind.
- Pruning releases changes what `compute-version` sees. It derives the next
  `-forgeguard.<n>` from `gh release list`, so a **deleted** version line's
  counter resets while its git tag still exists — re-cutting `v0.19.x` or
  `v2026.7.1` would compute a suffix whose tag is already taken and fail to
  create it. Inert while the version line moves forward; check the tag list
  first if you ever deliberately re-cut an old line.

The inventory captured before the first run is in the
[2026-08-17 cleanup record](./2026-08-17-cleanup-record.md); the run itself
is a maintainer dispatch (dry-run first, read the plan, then apply).

## Related

- [Sync policy](../upstream-sync/sync-policy.md)
- [Patch inventory](../upstream-sync/patch-inventory.md)
- [Artifact verification](./artifact-verification.md)
- [2026-08-17 cleanup record](./2026-08-17-cleanup-record.md)
