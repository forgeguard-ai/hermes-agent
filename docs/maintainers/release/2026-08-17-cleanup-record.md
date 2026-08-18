# Release and artifact cleanup record — 2026-08-17

Pre-deletion inventory captured on 2026-08-17 while the retention policy was
being written. **Nothing had been deleted when this was taken** — the authoring
session could not delete (see the
[plan](../../agent-plans/2026-08-17-release-artifact-cleanup.md), "Capability
boundary"); the prune is a maintainer dispatch of
[`artifact-retention.yml`](../../../.github/workflows/artifact-retention.yml).
Retention policy: **keep the two most recent releases and their image builds**
(`keep_releases` = `keep_builds` = 2 — the policy was tightened from one
retained build to two before it merged, so the previous release's image always
survives for roll-back). Companion to the [Release process](./release-process.md).

The tables below are the inventory *at snapshot time*. `v0.20.4` shipped on
2026-08-18 before any run, so the first real run keeps `v0.20.4` + `v0.20.3`
and also removes `v0.20.2` — the workflow's own dry-run output is the
authoritative plan; this file is the historical inventory behind it.

This is append-only history. Do not edit it to reflect later state.

## Retained (at snapshot time)

| Release | Release id | Published | Assets | Commit |
|---|---|---|---|---|
| `v0.20.3` | `371499913` | 2026-08-17T02:39:43Z | 5 (623 MB) | `db40be650e5231c1745b5d937ec3142de86bda74` |
| `v0.20.2` | `371438369` | 2026-08-16T21:22:46Z | 5 (623 MB) | `bebb68f0bdb029b3d40468ffd5dcf85cba04f76e` |

The commit column is what reconstructs the GHCR coordinates for a retained build:
`runtime-<commit>` / `cli-<commit>` on `ghcr.io/forgeguard-ai/hermes-agent`.

Also retained, untouched by this cleanup:

- **All 12 fork release tags** — `v0.19.0`–`v0.19.3`, `v0.20.2`, `v0.20.3`, and
  `v2026.7.1-forgeguard.1` … `.6`. Only the Release objects were removed; every tag
  survives, so any of these can be re-released from the same commit.
- **The 12 inherited upstream date tags** — `v2026.3.12` … `v2026.6.5`.
  [`sync-policy.md`](../upstream-sync/sync-policy.md) enumerates upstream releases with
  `git tag -l 'v20*'` and merges them by tag, and one workflow falls back to
  `git describe --tags --abbrev=0`. Deleting these would change how that policy reads.

## Releases deleted (11)

The Release object and its uploaded assets are gone. **The git tag was left in place**
for every entry below, so each commit stays reachable.

### `v0.19.3` — release id `369240252`

- Name: Hermes Agent v0.19.3
- Published: 2026-08-12T12:58:01Z
- Assets: 5 (619.7 MB)

| Asset | Size | Downloads |
|---|---|---|
| `hermes-desktop-client-0.19.3-linux-amd64.deb` | 113.8 MB | 0 |
| `hermes-desktop-client-0.19.3-linux-x86_64.AppImage` | 141.6 MB | 0 |
| `hermes-desktop-client-0.19.3-linux-x86_64.rpm` | 93.1 MB | 0 |
| `hermes-desktop-client-0.19.3-mac-arm64.dmg` | 135.8 MB | 0 |
| `hermes-desktop-client-0.19.3-mac-arm64.zip` | 135.3 MB | 0 |

### `v0.19.2` — release id `367711797`

- Name: Hermes Agent v0.19.2
- Published: 2026-08-10T06:00:17Z
- Assets: 5 (619.8 MB)

| Asset | Size | Downloads |
|---|---|---|
| `hermes-desktop-client-0.19.2-linux-amd64.deb` | 113.8 MB | 0 |
| `hermes-desktop-client-0.19.2-linux-x86_64.AppImage` | 141.6 MB | 0 |
| `hermes-desktop-client-0.19.2-linux-x86_64.rpm` | 93.1 MB | 0 |
| `hermes-desktop-client-0.19.2-mac-arm64.dmg` | 135.8 MB | 1 |
| `hermes-desktop-client-0.19.2-mac-arm64.zip` | 135.3 MB | 0 |

### `v0.19.1` — release id `367468358`

- Name: Hermes Agent v0.19.1
- Published: 2026-08-09T12:09:52Z
- Assets: 5 (619.7 MB)

| Asset | Size | Downloads |
|---|---|---|
| `hermes-desktop-client-0.19.1-linux-amd64.deb` | 113.8 MB | 0 |
| `hermes-desktop-client-0.19.1-linux-x86_64.AppImage` | 141.6 MB | 0 |
| `hermes-desktop-client-0.19.1-linux-x86_64.rpm` | 93.1 MB | 0 |
| `hermes-desktop-client-0.19.1-mac-arm64.dmg` | 135.8 MB | 1 |
| `hermes-desktop-client-0.19.1-mac-arm64.zip` | 135.3 MB | 0 |

### `v0.19.0` — release id `357801025`

- Name: Hermes Agent v0.19.0
- Published: 2026-07-22T05:51:11Z
- Assets: 5 (618.9 MB)

| Asset | Size | Downloads |
|---|---|---|
| `hermes-desktop-client-0.19.0-linux-amd64.deb` | 112.9 MB | 0 |
| `hermes-desktop-client-0.19.0-linux-x86_64.AppImage` | 141.6 MB | 0 |
| `hermes-desktop-client-0.19.0-linux-x86_64.rpm` | 93.1 MB | 0 |
| `hermes-desktop-client-0.19.0-mac-arm64.dmg` | 135.8 MB | 1 |
| `hermes-desktop-client-0.19.0-mac-arm64.zip` | 135.3 MB | 0 |

### `2026.7.1` — release id `357115577`

- Name: 2026.7.1
- Published: 2026-07-21T04:35:48Z
- Assets: 0 (0.0 MB)
- No assets were ever attached.

### `v2026.7.1-forgeguard.6` — release id `357018116`

- Name: Hermes Agent v0.18.0 (ForgeGuard fork v2026.7.1-forgeguard.6)
- Published: 2026-07-20T22:13:02Z
- Assets: 5 (619.6 MB)

| Asset | Size | Downloads |
|---|---|---|
| `hermes-desktop-client-0.18.0-linux-amd64.deb` | 113.0 MB | 0 |
| `hermes-desktop-client-0.18.0-linux-x86_64.AppImage` | 141.8 MB | 0 |
| `hermes-desktop-client-0.18.0-linux-x86_64.rpm` | 93.2 MB | 0 |
| `hermes-desktop-client-0.18.0-mac-arm64.dmg` | 136.0 MB | 0 |
| `hermes-desktop-client-0.18.0-mac-arm64.zip` | 135.6 MB | 0 |

### `v2026.7.1-forgeguard.5` — release id `349170677`

- Name: Hermes Agent v0.18.0 (ForgeGuard fork v2026.7.1-forgeguard.5)
- Published: 2026-07-05T13:37:18Z
- Assets: 5 (620.4 MB)

| Asset | Size | Downloads |
|---|---|---|
| `hermes-desktop-client-0.18.0-linux-amd64.deb` | 113.8 MB | 0 |
| `hermes-desktop-client-0.18.0-linux-x86_64.AppImage` | 141.8 MB | 0 |
| `hermes-desktop-client-0.18.0-linux-x86_64.rpm` | 93.2 MB | 1 |
| `hermes-desktop-client-0.18.0-mac-arm64.dmg` | 136.0 MB | 1 |
| `hermes-desktop-client-0.18.0-mac-arm64.zip` | 135.6 MB | 0 |

### `v2026.7.1-forgeguard.4` — release id `349143205`

- Name: Hermes Agent v0.18.0 (ForgeGuard fork v2026.7.1-forgeguard.4)
- Published: 2026-07-05T10:51:36Z
- Assets: 5 (620.5 MB)

| Asset | Size | Downloads |
|---|---|---|
| `hermes-desktop-client-0.18.0-linux-amd64.deb` | 113.8 MB | 0 |
| `hermes-desktop-client-0.18.0-linux-x86_64.AppImage` | 141.8 MB | 0 |
| `hermes-desktop-client-0.18.0-linux-x86_64.rpm` | 93.2 MB | 0 |
| `hermes-desktop-client-0.18.0-mac-arm64.dmg` | 136.0 MB | 0 |
| `hermes-desktop-client-0.18.0-mac-arm64.zip` | 135.6 MB | 0 |

### `v2026.7.1-forgeguard.3` — release id `348866236`

- Name: Hermes Agent v0.18.0 (ForgeGuard fork v2026.7.1-forgeguard.3)
- Published: 2026-07-04T04:57:11Z
- Assets: 5 (620.5 MB)

| Asset | Size | Downloads |
|---|---|---|
| `hermes-desktop-client-0.18.0-linux-amd64.deb` | 113.8 MB | 0 |
| `hermes-desktop-client-0.18.0-linux-x86_64.AppImage` | 141.8 MB | 0 |
| `hermes-desktop-client-0.18.0-linux-x86_64.rpm` | 93.2 MB | 1 |
| `hermes-desktop-client-0.18.0-mac-arm64.dmg` | 136.0 MB | 1 |
| `hermes-desktop-client-0.18.0-mac-arm64.zip` | 135.6 MB | 0 |

### `v2026.7.1-forgeguard.2` — release id `348327467`

- Name: Hermes Agent v0.18.0 (ForgeGuard fork v2026.7.1-forgeguard.2)
- Published: 2026-07-02T22:51:34Z
- Assets: 5 (620.5 MB)

| Asset | Size | Downloads |
|---|---|---|
| `hermes-desktop-client-0.18.0-linux-amd64.deb` | 113.8 MB | 0 |
| `hermes-desktop-client-0.18.0-linux-x86_64.AppImage` | 141.8 MB | 0 |
| `hermes-desktop-client-0.18.0-linux-x86_64.rpm` | 93.2 MB | 0 |
| `hermes-desktop-client-0.18.0-mac-arm64.dmg` | 136.0 MB | 1 |
| `hermes-desktop-client-0.18.0-mac-arm64.zip` | 135.6 MB | 0 |

### `v2026.7.1-forgeguard.1` — release id `348180830`

- Name: Hermes Agent v0.18.0 (ForgeGuard fork v2026.7.1-forgeguard.1)
- Published: 2026-07-02T17:02:02Z
- Assets: 5 (622.4 MB)

| Asset | Size | Downloads |
|---|---|---|
| `hermes-desktop-client-0.18.0-linux-amd64.deb` | 113.8 MB | 0 |
| `hermes-desktop-client-0.18.0-linux-x86_64.AppImage` | 141.8 MB | 0 |
| `hermes-desktop-client-0.18.0-linux-x86_64.rpm` | 93.2 MB | 1 |
| `hermes-desktop-client-0.18.0-mac-arm64.dmg` | 137.0 MB | 1 |
| `hermes-desktop-client-0.18.0-mac-arm64.zip` | 136.6 MB | 0 |

**Total: 11 releases, 6.20 GB of assets, 10 lifetime downloads
across all of them.** The retained two account for a further 1245 MB.

## Git tags deleted (7)

None of these were release tags. The first six point at commits that are **not in
`main`'s history** — once the tag is gone those commits are unreachable and eligible
for garbage collection, so the SHAs below are the only remaining handle on them.
While a copy survives on the remote or in any clone, recover one with
`git fetch origin <sha>` or `git checkout <sha>`.

| Tag | Commit | Date | In `main`'s history? |
|---|---|---|---|
| `premerge-oh-god` | `a08725e52a17964b3c91b12fa434f4cba45c4521` | 2026-05-28 | no |
| `merge-commit-backup` | `48a7e137b1f9ef4362039f124798faadc6755bcb` | 2026-05-28 | no |
| `clean-before-remerge` | `0fce82164ad9b92a104776bf9b0363f73be0dd33` | 2026-05-29 | no |
| `desktop-pr20059-installers` | `bff052d61fa30b433b93331c57535af5b0123c37` | 2026-05-11 | no |
| `backup/precopystrip-20260616-2058` | `a348fc1cccc29841a83d451995a81868e991fa4c` | 2026-06-16 | no |
| `backup/opentui-prestrip-20260616-1950` | `9d05f3721d69df570fde4c9378d5ed252f53ca88` | 2026-06-16 | no |
| `2026.7.1` | `1d7b37211ac3e1b263afa05c9f903276740105b8` | 2026-07-20 | yes |

`2026.7.1` was a stray no-`v` duplicate of `v2026.7.1-forgeguard.6`'s commit carrying
a zero-asset Release; its commit stays reachable from `main`.

## How this cleanup executes

Nothing here was deleted by the session that planned it. That session's token is
allowed to create and push but **not** to delete: releases, workflow artifacts,
GHCR versions and git refs all returned `403`, and `git push --dry-run --delete`
reported a false success because dry-run never sends the ref update. So the whole
cleanup ships as two dispatchable workflows a maintainer runs:

| Workflow | Deletes | First-run inputs |
|---|---|---|
| [`artifact-retention.yml`](../../../.github/workflows/artifact-retention.yml) | releases, GHCR versions, workflow artifacts, strays named in `delete_tags` | `keep_releases=2`, `keep_builds=1`, `delete_tags=2026.7.1` |
| [`branch-cleanup.yml`](../../../.github/workflows/branch-cleanup.yml) | merged remote branches | `keep=dev` |

Both default to `dry_run: true`. Run each dry first and read the plan.

The six backup tags in the table above are **not** deletable by either workflow —
`artifact-retention.yml` only removes tags named in `delete_tags`, and that input
exists for strays whose Release had to go first. Delete them by hand once you are
satisfied the SHAs are recorded:

```bash
git push origin --delete \
  refs/tags/premerge-oh-god \
  refs/tags/merge-commit-backup \
  refs/tags/clean-before-remerge \
  refs/tags/desktop-pr20059-installers \
  refs/tags/backup/precopystrip-20260616-2058 \
  refs/tags/backup/opentui-prestrip-20260616-1950
```

## Consequence for release numbering

[`release-on-merge.yml`](../../../.github/workflows/release-on-merge.yml) computes the
next version by parsing `gh release list --limit 200` for `-forgeguard.<n>` suffixes.
That listing no longer sees the deleted releases, so re-cutting a **deleted** version
line would compute a suffix whose git tag still exists, and tag creation would fail.
This is inert while the version line moves forward from `0.20.x` — it only bites if
someone deliberately re-cuts `v0.19.x` or `v2026.7.1`.
