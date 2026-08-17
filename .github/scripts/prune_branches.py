#!/usr/bin/env python3
"""Delete stale remote branches that are fully merged into the default branch.

Safe by construction — a branch is deleted only when every one of these holds:

* it is not the default branch;
* it is not named by ``--keep`` (repeatable);
* it is not protected;
* it is not the head of an **open** pull request;
* its tip is an ancestor of the default branch, i.e. it has no commits the
  default branch lacks — unless the branch is named by ``--force-delete``.

``--force-delete`` is the only way to remove a branch carrying unmerged commits,
and it must name the branch explicitly. Use it for work that landed by another
route (a reworked PR, a squash) where the commits are superseded rather than
lost. Verify that yourself first: this script checks reachability, not intent.

Runs in dry-run mode unless ``--apply`` is passed. Driven by
``.github/workflows/branch-cleanup.yml``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"


class Http:
    def __init__(self, token: str) -> None:
        self._token = token

    def _request(self, method: str, url: str):
        req = urllib.request.Request(url, method=method)
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read()
                return resp.status, (json.loads(body) if body else None)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            try:
                detail = json.loads(body).get("message", body)
            except ValueError:
                detail = body
            return exc.code, {"message": detail}

    def get(self, path: str):
        return self._request("GET", f"{API}{path}")

    def delete(self, path: str):
        return self._request("DELETE", f"{API}{path}")

    def paginate(self, path: str):
        page = 1
        joiner = "&" if "?" in path else "?"
        while True:
            status, body = self.get(f"{path}{joiner}per_page=100&page={page}")
            if status != 200:
                message = (body or {}).get("message", "unknown error")
                raise RuntimeError(f"GET {path} page {page} -> HTTP {status}: {message}")
            if not body:
                return
            yield from body
            if len(body) < 100:
                return
            page += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument(
        "--keep",
        action="append",
        default=[],
        help="Branch to keep even when merged. Repeatable. The default branch is always kept.",
    )
    parser.add_argument(
        "--force-delete",
        action="append",
        default=[],
        help="Branch to delete even with unmerged commits. Repeatable. Verify first.",
    )
    parser.add_argument(
        "--max-delete",
        type=int,
        default=20,
        help="Abort if the plan exceeds this many branches (runaway guard).",
    )
    parser.add_argument("--apply", action="store_true", help="Delete for real.")
    args = parser.parse_args()

    if not args.repo or "/" not in args.repo:
        print("::error::--repo must be owner/name", file=sys.stderr)
        return 2
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("::error::GITHUB_TOKEN is not set", file=sys.stderr)
        return 2

    http = Http(token)
    print(f"Branch cleanup for {args.repo} [{'APPLY' if args.apply else 'DRY RUN'}]")

    status, repo_info = http.get(f"/repos/{args.repo}")
    if status != 200:
        print(f"::error::cannot read repo: {(repo_info or {}).get('message')}", file=sys.stderr)
        return 1
    default_branch = repo_info["default_branch"]

    keep = set(args.keep) | {default_branch}
    force = set(args.force_delete)
    print(f"  default branch: {default_branch}")
    print(f"  keep: {', '.join(sorted(keep))}")
    if force:
        print(f"  force-delete: {', '.join(sorted(force))}")

    try:
        branches = list(http.paginate(f"/repos/{args.repo}/branches"))
        open_prs = list(http.paginate(f"/repos/{args.repo}/pulls?state=open"))
    except RuntimeError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    # A branch with an open PR is live work regardless of merge state.
    pr_heads = {
        pr["head"]["ref"]: pr["number"]
        for pr in open_prs
        if pr["head"]["repo"] and pr["head"]["repo"]["full_name"] == args.repo
    }
    print(f"  {len(branches)} branches, {len(open_prs)} open PRs\n")

    doomed: list[str] = []
    for branch in sorted(b["name"] for b in branches):
        info = next(b for b in branches if b["name"] == branch)

        if branch in keep:
            print(f"  KEEP    {branch:<52} (protected by policy)")
            continue
        if info.get("protected"):
            print(f"  KEEP    {branch:<52} (branch protection)")
            continue
        if branch in pr_heads:
            print(f"  KEEP    {branch:<52} (open PR #{pr_heads[branch]})")
            continue

        # Reachability: is the branch tip an ancestor of the default branch?
        status, cmp_info = http.get(
            f"/repos/{args.repo}/compare/"
            f"{urllib.parse.quote(default_branch)}...{urllib.parse.quote(branch)}"
        )
        if status != 200:
            print(f"  KEEP    {branch:<52} (compare failed: HTTP {status})")
            continue
        ahead, behind = cmp_info["ahead_by"], cmp_info["behind_by"]

        if ahead == 0:
            print(f"  DELETE  {branch:<52} (merged, {behind} behind)")
            doomed.append(branch)
        elif branch in force:
            print(f"  DELETE  {branch:<52} (FORCED — {ahead} unmerged, {behind} behind)")
            doomed.append(branch)
        else:
            print(f"  KEEP    {branch:<52} ({ahead} unmerged commits)")

    print(f"\n=== Summary: {len(doomed)} branches to delete ===")
    if not doomed:
        print("Nothing to do.")
        return 0
    if len(doomed) > args.max_delete:
        print(
            f"::error::plan of {len(doomed)} exceeds --max-delete {args.max_delete}; "
            "aborting. Re-run with a higher cap if the plan is genuinely correct."
        )
        return 1

    if not args.apply:
        print("\nDry run — nothing deleted. Re-run with apply=true to execute.")
        return 0

    failures = 0
    for branch in doomed:
        status, body = http.delete(
            f"/repos/{args.repo}/git/refs/heads/{urllib.parse.quote(branch)}"
        )
        if status in (200, 202, 204):
            print(f"  deleted {branch}")
        else:
            print(f"  ::error::failed {branch}: HTTP {status} {(body or {}).get('message')}")
            failures += 1

    if failures:
        print(f"\n::error::{failures} deletion(s) failed")
        return 1
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
