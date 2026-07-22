# Upstream sync policy (ForgeGuard fork)

A step-by-step, agent-agnostic runbook for syncing `ForgeGuard/hermes-agent`
(this fork) to a new `NousResearch/hermes-agent` (upstream) release tag. Works
the same whether you're Cursor, GitHub Copilot, Codex, or Claude Code — it's
plain git + `gh` CLI, no tool-specific features required.

Run this periodically (roughly whenever upstream cuts a new tagged release you
want the fork to track) — not on every upstream commit. The fork deliberately
syncs to **tagged releases**, not the moving `upstream/main` tip, so the fork's
own history has stable, reproducible sync points.

This runbook has two companions, both of which are load-bearing and must be
worked through as part of every sync:

- [Patch inventory](./patch-inventory.md) — the fork-patch re-verification
  checklist (step 4).
- [Conflict resolution](./conflict-resolution.md) — how to resolve conflicts and
  triage the test suite (steps 4–5).

## Prerequisites

- `origin` remote = `ForgeGuard/hermes-agent` (this fork, push access).
- An `upstream` remote pointing at `NousResearch/hermes-agent` (read-only — never
  push here). Add it once if missing:

  ```bash
  git remote add upstream https://github.com/NousResearch/hermes-agent.git
  ```

- `gh` CLI authenticated against a ForgeGuard account with write access to the
  fork.
- A working Python venv (`.venv` or `venv`) with dependencies installed — you'll
  run the full test suite before opening the PR.

## Step-by-step

### 1. Fetch upstream and pick the target tag

```bash
git fetch upstream --tags
git tag -l 'v20*' --sort=-creatordate | head -5   # see recent upstream release tags
```

Pick the **newest tagged release** you want to sync to (not `upstream/main`
directly — that moves under you mid-sync). Confirm it looks right:

```bash
git log -1 <TAG> --format="%H %s %ci"
```

### 2. Create the sync branch off fork `main`

```bash
git checkout main
git pull origin main
git checkout -b sync/upstream-<TAG>
```

Example branch name: `sync/upstream-v2026.7.1`.

### 3. Merge the upstream tag (real merge, never squash/rebase)

```bash
git merge <TAG> --no-edit -m "Merge upstream <TAG> into fork main"
```

A real merge commit (two parents: fork `main` + the upstream tag) is required —
it's what lets a *future* sync's `git merge` correctly compute the three-way diff
against the last sync point. Squashing or rebasing here would make every
subsequent sync re-resolve the same conflicts from scratch. See
[Why a real merge](#why-a-real-merge-not-rebase-or-squash).

Expect conflicts to be **small and additive** — the fork's changes touch a
narrow, well-isolated set of files (see the [patch inventory](./patch-inventory.md)).
If a sync ever produces conflicts far outside that list, stop and investigate
before resolving; see [Conflict resolution](./conflict-resolution.md).

### 4. Resolve conflicts, then re-verify the fork-patch checklist

Resolve any real conflicts first (`git status` to list them, fix, `git add`),
following [Conflict resolution](./conflict-resolution.md). Whatever the merge
conflict outcome, **explicitly re-verify** every item in the
[patch inventory](./patch-inventory.md) is still present and correct on the
merged branch — a clean auto-merge can silently keep the wrong side, and those
are exactly the places most likely to matter to the fork's own CI/release
behaviour.

### 5. Run the test suite

```bash
scripts/run_tests.sh
```

Triage every failure per [Conflict resolution → Triaging the test suite](./conflict-resolution.md#triaging-the-test-suite):
pre-existing upstream debt is noted in the PR and not blocked on; a failure that
reproduces only on the merged branch is a real merge regression and must be fixed
before opening the PR.

### 6. Update `FORK_UPSTREAM_BASE`

```bash
echo "<TAG>" > FORK_UPSTREAM_BASE
git add FORK_UPSTREAM_BASE
git commit -m "chore: bump FORK_UPSTREAM_BASE to <TAG>"
```

This file is read by `release-on-merge.yml`'s version-computation step for the
"Upstream release" traceability line in the release notes. Since Hermes 0.19.0
it no longer names the release — release tags are the `pyproject.toml` product
semver (`v<hermes-version>`, with a `-forgeguard.<n>` suffix only on a re-cut
of an already-released version) — but the marker must still be correct: without
it, that workflow falls back to `git describe --tags --abbrev=0`, which can
pick an unrelated or stale tag. See the
[Release process](../release/release-process.md).

### 7. Push and open the PR

```bash
git push -u origin sync/upstream-<TAG>
gh pr create --repo ForgeGuard/hermes-agent \
  --title "sync: merge upstream <TAG> into fork main" \
  --base main --head sync/upstream-<TAG> \
  --body "..."
```

Use a **real merge** to land it too (`gh pr merge <N> --merge
--delete-branch=false`), matching this branch's own merge commit — squashing the
PR would throw away the two-parent merge commit structure step 3 relies on for
the *next* sync.

Do **not** open this PR with `head = NousResearch:<branch>` (an upstream branch
directly) — always push your own `sync/upstream-<TAG>` branch to `origin` first
and PR from that. Using an upstream branch as the head means every new commit
pushed to that branch upstream re-triggers a `synchronize` event on your PR,
flooding the fork's Actions tab with blocked "Action required" runs (harmless but
noisy).

### 8. Verify CI and the resulting release

After merging, confirm:

- `ci.yml`'s required checks pass on the merge commit.
- `release-on-merge.yml` fires (a sync PR always touches release-relevant paths,
  so the release gate lets it through), completes fully green, and — check
  individual **step** conclusions, not just job conclusions — actually uploads
  installers and pushes both runtime images rather than silently skipping.
- The resulting GitHub Release is tagged with the product version on the merged
  branch — e.g. `v0.19.0`; a sync normally bumps the product version, so expect
  the plain tag, or the next `-forgeguard.<n>` re-cut suffix if that version
  had already released — its notes' "Upstream release" line shows `<TAG>`, and
  it has all 5 installers attached (`*.deb`, `*.AppImage`, `*.rpm`, `*.dmg`,
  `*.zip`).

## Why a real merge, not rebase or squash

- **Rebase** would rewrite every fork-only commit's hash and require
  force-pushing `main`, which this repo's git-safety rules forbid.
- **Squash** collapses the two-parent merge structure into one commit whose only
  parent is fork `main` — the next sync's `git merge <newer-tag>` would then have
  to recompute conflicts against the *entire* upstream history since the fork
  point, instead of just the commits between the two tags.
- A **real merge** keeps both parent lineages intact, so each subsequent sync
  only needs to resolve the diff since the *previous* sync tag — the conflict
  surface stays small and bounded release-over-release.

## Related

- [Patch inventory](./patch-inventory.md)
- [Conflict resolution](./conflict-resolution.md)
- [Release process](../release/release-process.md)
