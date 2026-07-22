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
- The product version only bumps on upstream syncs, but the workflow fires on
  every release-relevant merge — so a **re-cut** of an already-released product
  version (e.g. a fork-only fix) gets a `-forgeguard.<n>` suffix instead of
  colliding on a duplicate tag: `v0.19.0-forgeguard.2`, counting the plain tag
  as cut 1. `<n>` is computed by scanning existing release tags.

The upstream base tag no longer names the release. It is still read from the
`FORK_UPSTREAM_BASE` marker file at the repo root — which the
[upstream-sync runbook](../upstream-sync/sync-policy.md) rewrites on every sync —
but now only feeds the "Upstream release" traceability line in the release
notes. The marker must still always be present and correct: if it is missing,
`compute-version` falls back to `git describe --tags --abbrev=0`, which can pick
an unrelated or stale tag.

Releases up to `v2026.7.1-forgeguard.3` used the old date-shaped
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
   installers (`.AppImage`, `.deb`, `.rpm`) and ad-hoc-signed macOS installers
   (`.dmg`, `.zip`). It does **not** pass a `version:` input; desktop artifacts
   are versioned only by the Release tag.
3. Calls `build-runtime-images.yml` with `push: true` and
   `version: <computed version>` → builds, tests, and pushes both image variants
   to `ghcr.io/forgeguard-ai/hermes-agent` with tags `runtime-<sha>` /
   `runtime-latest` / `runtime-<version>` and `cli-<sha>` / `cli-latest` /
   `cli-<version>`.
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
| `runtime-<version>` / `cli-<version>` | immutable | pin deployments to a specific fork release |
| `runtime-<git-sha>` / `cli-<git-sha>` | immutable | trace any image back to its exact commit |
| `runtime-latest` / `cli-latest` | rolling | testing / always-newest |

See [Image tags](../../site/reference/image-tags.md) for the consumer-facing
description of the two variants and how to run them.

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
  expected "Upstream release" line, and it has all five installers attached
  (`*.deb`, `*.AppImage`, `*.rpm`, `*.dmg`, `*.zip`).

See [Artifact verification](./artifact-verification.md) for provenance checks on
the published images and installers.

## Related

- [Sync policy](../upstream-sync/sync-policy.md)
- [Patch inventory](../upstream-sync/patch-inventory.md)
- [Artifact verification](./artifact-verification.md)
