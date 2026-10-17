# Conflict resolution (ForgeGuard fork)

How to resolve merge conflicts and triage the test suite during an
[upstream sync](./sync-policy.md). Used in steps 4–5 of the runbook.

## Expected conflict surface

The fork's changes touch a narrow, well-isolated set of files — see the
[patch inventory](./patch-inventory.md). Expect conflicts to be **small and
additive**.

If a sync ever produces conflicts far outside that list, **stop and investigate
before resolving**. It likely means one of:

- upstream touched a fork-owned file in a way this runbook doesn't yet
  anticipate (update the [patch inventory](./patch-inventory.md) once understood),
  or
- a previous sync resolved something incorrectly and the damage is only now
  surfacing.

## Resolving a real conflict

1. List conflicts with `git status`.
2. For each, resolve then `git add` the file.
3. When upstream touches one of the fork-patched files in a way that creates a
   real (non-trivial) conflict, resolve it by **keeping upstream's substantive
   change and re-applying the fork-only delta on top**, rather than reverting to
   the fork's pre-sync version wholesale — the fork almost never wants to reject
   an upstream improvement to a file it also patches. Example: if upstream
   restructures the `Dockerfile`, re-apply their change inside the matching
   fork stage rather than reverting the multi-target split.

### When upstream splits or moves a file the fork patches

Upstream periodically splits a large module into several (a web server's routes
into a `web_routers/` package, a session handler into per-method modules), or
moves code to a new path. Git reports a conflict in the old file, or none at
all, while the fork's change belongs in a file that only exists on upstream's
side.

- **Never resolve a split file to upstream's side without porting the fork's
  change** into the module where the code now lives. Resolving to upstream
  silently drops the fork patch, and the tests that cover it may have moved or
  been deleted too.
- If the port can't be done inside the merge commit, resolve to upstream, list
  the file as *pending port* in the merge commit message (sync-policy step 3),
  and port it in its own commit on `dev` before the PR. The PR description
  repeats the list with each port's commit.
- Prefer the fork's own modules: fork logic that lives in a fork-owned file
  (`tests/fork/`, a fork helper module called from one line upstream) survives
  splits untouched, and only the one-line hook needs re-placing. When a port is
  large, move the fork logic into such a module as part of the port.

### Files upstream deletes

A modify/delete conflict means upstream removed a file the fork changed. Find
out why (`git log --diff-filter=D -1 <COMMIT> -- <path>` on upstream's side),
then either accept the deletion, re-homing any fork cases first (fork tests
belong in `tests/fork/`), or port the fork behaviour to wherever upstream moved
the code. Never resurrect a deleted upstream file by accident.

## Re-verify after resolving

A clean auto-merge can silently keep the wrong side. Regardless of the conflict
outcome, walk the entire [patch inventory](./patch-inventory.md) and confirm each
fork patch is still present and correct on the merged branch. This is not
optional — the highest-risk regressions here produce a green CI run while
silently disabling a fork guard or an installer upload.

## Triaging the test suite

Run the suite with the repo wrapper (never bare `pytest`):

```bash
scripts/run_tests.sh
```

A merge this size (hundreds of files, hundreds of commits) can surface a handful
of pre-existing or environment-sensitive failures unrelated to the sync (flaky
wall-clock tests, jsdom gaps in `apps/desktop`'s `test:ui`, etc. — see
`AGENTS.md`'s "Known Pitfalls"). Triage every failure:

- **Pre-existing upstream debt.** If it reproduces identically on a clean
  checkout of the upstream tag alone (no fork changes), note it in the PR
  description and don't block on it.
- **Real merge regression.** If it only reproduces on the merged branch, fix it
  before opening the PR.

## Related

- [Sync policy](./sync-policy.md)
- [Patch inventory](./patch-inventory.md)
