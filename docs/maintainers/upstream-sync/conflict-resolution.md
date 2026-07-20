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
