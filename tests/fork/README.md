# tests/fork/

Tests for fork-owned behavior that must survive upstream syncs.

Upstream is free to delete, rename or rewrite its own test files. When a fork
patch's test cases live inside an upstream-owned test file, an upstream
deletion turns into a modify/delete conflict at the next sync, and the fork's
cases are easy to lose by accepting the deletion. Test files in this directory
are owned by the fork alone, so a sync can accept upstream's deletions without
dropping any fork coverage.

Rules:

- Put the cases for a fork patch here, not in an upstream test file, whenever
  the patch is fork-only.
- Name the file after the fork behavior it covers, not after the upstream file
  it came from.
- List each file in `docs/maintainers/upstream-sync/patch-inventory.md` next to
  the patch it verifies.
