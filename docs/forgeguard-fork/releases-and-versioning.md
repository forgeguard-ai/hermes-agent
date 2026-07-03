# Fork releases and versioning

## Version scheme

Fork releases are tagged `<upstream-base>-forgeguard.<n>`, e.g.
`v2026.7.1-forgeguard.3`:

- `<upstream-base>` is the upstream `NousResearch/hermes-agent` release tag
  the fork's `main` is currently synced to. It is read from the
  `FORK_UPSTREAM_BASE` marker file at the repo root, which the
  [upstream-sync runbook](upstream-sync-skill.md) rewrites on every sync.
- `<n>` auto-increments per base tag by scanning existing releases.

Each release also surfaces the actual Hermes Agent product version (from
`pyproject.toml`) in its title and notes, since the fork tag says which
upstream *release line* it tracks, not which product version it contains.

## What gets published, and when

`release-on-merge.yml` runs when a PR merges into `main` and the change is
release-relevant. It skips (no release, no builds) when the PR carries the
`no-release` label or touches no release-relevant paths (docs-only and
CI-only merges don't produce releases). For qualifying merges it:

1. Computes the next `<base>-forgeguard.<n>` version.
2. Calls `build-desktop-client.yml` → unsigned Linux installers
   (`.AppImage`, `.deb`, `.rpm`) and ad-hoc-signed macOS installers
   (`.dmg`, `.zip`).
3. Calls `build-runtime-images.yml` → builds, tests, and pushes both image
   variants to `ghcr.io/forgeguard/hermes-agent` with tags
   `runtime-<sha>` / `runtime-latest` / `runtime-<version>` and
   `cli-<sha>` / `cli-latest` / `cli-<version>`.
4. Publishes a GitHub Release with the installers attached and the image
   pull commands in the notes.

Those two build workflows have no triggers of their own besides
`workflow_dispatch` (the manual escape hatch — e.g. validating a branch's
images with `push=false`); the release workflow is the single merge-time
builder.

## Image tag families

| Tag | Mutability | Use |
| --- | --- | --- |
| `runtime-<version>` / `cli-<version>` | immutable | pin deployments to a specific fork release |
| `runtime-<git-sha>` / `cli-<git-sha>` | immutable | trace any image back to its exact commit |
| `runtime-latest` / `cli-latest` | rolling | testing / always-newest |

See [runtime-images.md](runtime-images.md) for what the two variants
contain and how to run them.

## macOS installer note

The fork has no Apple Developer credentials, so macOS builds are ad-hoc
signed (NOT notarized). Gatekeeper quarantines the downloaded `.dmg` as
"damaged"; after copying Hermes.app to /Applications run once:

```bash
xattr -cr /Applications/Hermes.app
```

(Downloading the `.zip` with `curl -L` avoids the quarantine attribute
entirely.)
