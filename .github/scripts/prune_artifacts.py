#!/usr/bin/env python3
"""Retention prune for ForgeGuard fork publishing artifacts.

Deletes, in this order:

1. GitHub Releases beyond the newest ``--keep-releases``. Their **git tags are
   left in place**, so every release stays rebuildable from source at the exact
   commit — only the Release object and its uploaded installers go away.
2. GHCR container versions of ``ghcr.io/<owner>/hermes-agent`` outside a keep
   set derived from the newest ``--keep-builds`` releases.
3. Workflow artifacts, keeping the newest N per name for the desktop installer
   artifacts and dropping every other unexpired artifact — except that nothing
   younger than ``--min-age-hours`` is touched, so a prune dispatched while CI
   is running never removes an artifact a ``workflow_run`` consumer (the CI
   review comment, the test-durations merge) is about to download.
4. Any git tag named by ``--delete-tag`` (for strays whose Release had to go
   first, so a release never dangles at a missing tag).

Runs in dry-run mode unless ``--apply`` is passed. Driven by
``.github/workflows/artifact-retention.yml``; see
``docs/maintainers/release/release-process.md``.

Three guards matter more than the rest, because getting any of them wrong is
either destructive or expensive to undo:

* **Untagged GHCR versions are never deleted.** ``build-runtime-images.yml``
  writes a buildkit registry cache (``mode=max``) into this same package. Its
  index references a large set of untagged manifests, so a "delete untagged
  versions" sweep both destroys the cache and can orphan layers the index still
  points at.
* **Only packages in PACKAGES are touched.** The ``forgeguard-ai`` GHCR
  namespace also holds ``camofox-browser``, ``kokoro-server*`` and
  ``faster-whisper-server*``, which this repo does not build and deployments pin
  at runtime. The namespace is never enumerated.
* **Release git tags survive.** Only ``--delete-tag`` removes a tag, and only
  the tags named explicitly on the command line.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"

# GHCR packages this repo owns. Never enumerate the namespace — see module docstring.
PACKAGES = ("hermes-agent",)

# Image tag prefixes published per build target by build-runtime-images.yml.
TARGETS = ("runtime", "cli")

# Tags that are always kept regardless of release age.
#   *-latest      rolling; agent-command's default deployment image resolves here
#   buildcache-*  buildkit registry cache indexes, not deployable images
ALWAYS_KEEP_TAGS = frozenset(
    [f"{t}-latest" for t in TARGETS]
    + [f"buildcache-{t}-amd64" for t in TARGETS]
)

# Artifact names to retain, mapped to how many of the newest to keep. Anything
# not listed here is dropped when it has not already expired (and is older than
# --min-age-hours). These are the per-platform uploads of build-desktop-client.yml
# that release-on-merge.yml downloads into a release; once released they are
# only a re-download convenience.
KEEP_NEWEST_ARTIFACTS = {
    "hermes-desktop-linux": 1,
    "hermes-desktop-macos": 1,
    "hermes-desktop-windows": 1,
}

# Artifacts younger than this are never deleted, whatever their name: the
# review-status-* / test-durations-slice-* / ci-timings-report artifacts are
# consumed by workflow_run jobs minutes after upload, and the desktop artifacts
# of an in-flight release are downloaded by release-on-merge.yml.
DEFAULT_MIN_AGE_HOURS = 24


class Http:
    def __init__(self, token: str, package_token: str | None = None) -> None:
        self._token = token
        self._package_token = package_token or token

    def _request(self, method: str, url: str, *, packages: bool = False):
        token = self._package_token if packages else self._token
        req = urllib.request.Request(url, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read()
                return resp.status, (json.loads(body) if body else None)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(body)
                detail = parsed.get("message", body)
            except ValueError:
                detail = body
            return exc.code, {"message": detail}

    def get(self, path: str, *, packages: bool = False):
        return self._request("GET", f"{API}{path}", packages=packages)

    def delete(self, path: str, *, packages: bool = False):
        return self._request("DELETE", f"{API}{path}", packages=packages)

    def paginate(self, path: str, *, packages: bool = False):
        """Yield every item across pages, stopping on the first error."""
        page = 1
        joiner = "&" if "?" in path else "?"
        while True:
            status, body = self.get(
                f"{path}{joiner}per_page=100&page={page}", packages=packages
            )
            if status != 200:
                message = (body or {}).get("message", "unknown error")
                raise RuntimeError(f"GET {path} page {page} -> HTTP {status}: {message}")
            if not body:
                return
            items = body if isinstance(body, list) else body.get("artifacts", [])
            if not items:
                return
            yield from items
            if len(items) < 100:
                return
            page += 1


class Plan:
    """Accumulates intended deletions and reports them as one auditable list."""

    def __init__(self) -> None:
        self.entries: list[tuple[str, str, str]] = []
        self.failures = 0

    def add(self, kind: str, label: str, path: str) -> None:
        self.entries.append((kind, label, path))

    def of(self, kind: str) -> list[tuple[str, str, str]]:
        return [e for e in self.entries if e[0] == kind]


def resolve_tag_commit(http: Http, repo: str, tag: str) -> str | None:
    """Full commit SHA a tag resolves to, following annotated tags."""
    status, body = http.get(f"/repos/{repo}/git/ref/tags/{urllib.parse.quote(tag)}")
    if status != 200:
        return None
    obj = body["object"]
    if obj["type"] == "commit":
        return obj["sha"]
    status, body = http.get(f"/repos/{repo}/git/tags/{obj['sha']}")
    if status != 200:
        return None
    return body["object"]["sha"]


def collect(http: Http, path: str, plan: Plan, what: str) -> list | None:
    """Paginate, or report the failure and return None so planning continues."""
    try:
        return list(http.paginate(path))
    except RuntimeError as exc:
        print(f"  ::error::{what}: {exc}")
        plan.failures += 1
        return None


def plan_releases(http: Http, repo: str, keep: int, plan: Plan) -> list[dict]:
    """Plan release deletions; return the releases being kept, newest first."""
    releases = collect(http, f"/repos/{repo}/releases", plan, "releases")
    if releases is None:
        print("\n=== Releases: unreadable, skipped ===")
        return []
    releases.sort(key=lambda r: r.get("published_at") or r["created_at"], reverse=True)
    kept, doomed = releases[:keep], releases[keep:]

    print(f"\n=== Releases ({len(releases)} total, keeping newest {keep}) ===")
    for r in kept:
        size = sum(a["size"] for a in r["assets"])
        print(f"  KEEP    {r['tag_name']:<28} {len(r['assets'])} assets, {size / 1e6:.0f} MB")
    for r in doomed:
        size = sum(a["size"] for a in r["assets"])
        print(f"  DELETE  {r['tag_name']:<28} {len(r['assets'])} assets, {size / 1e6:.0f} MB (git tag kept)")
        plan.add("release", r["tag_name"], f"/repos/{repo}/releases/{r['id']}")
    return kept


def plan_packages(
    http: Http, owner: str, repo: str, kept_releases: list[dict], keep_builds: int, plan: Plan
) -> None:
    keep_tags = set(ALWAYS_KEEP_TAGS)
    for release in kept_releases[:keep_builds]:
        tag = release["tag_name"]
        for target in TARGETS:
            keep_tags.add(f"{target}-{tag}")
        sha = resolve_tag_commit(http, repo, tag)
        if sha:
            for target in TARGETS:
                keep_tags.add(f"{target}-{sha}")
        else:
            print(f"  ::warning::could not resolve commit for {tag}; its -<sha> image tags are unprotected")

    print(f"\n=== GHCR (keeping images for the newest {keep_builds} release(s)) ===")
    print("  keep tags: " + ", ".join(sorted(keep_tags)))

    for package in PACKAGES:
        encoded = urllib.parse.quote(package, safe="")
        base = f"/orgs/{owner}/packages/container/{encoded}"
        try:
            versions = list(http.paginate(f"{base}/versions", packages=True))
        except RuntimeError as exc:
            print(f"  ::error::{package}: {exc}")
            print(
                "  GITHUB_TOKEN cannot read this package. Set the GHCR_CLEANUP_TOKEN "
                "secret to a PAT with read:packages + delete:packages and re-run."
            )
            plan.failures += 1
            continue

        print(f"\n  -- {package}: {len(versions)} versions --")
        for version in versions:
            tags = version.get("metadata", {}).get("container", {}).get("tags", [])
            label = ",".join(tags) if tags else "<untagged>"
            # Guard: untagged versions carry the buildkit cache. Never delete.
            if not tags:
                continue
            if any(t in keep_tags for t in tags):
                print(f"     KEEP    {label}")
                continue
            print(f"     DELETE  {label}")
            plan.add("package", f"{package}:{label}", f"{base}/versions/{version['id']}")

        untagged = sum(
            1
            for v in versions
            if not v.get("metadata", {}).get("container", {}).get("tags", [])
        )
        print(f"     ({untagged} untagged versions skipped — buildkit cache)")


def _created_at(artifact: dict) -> datetime:
    return datetime.fromisoformat(artifact["created_at"].replace("Z", "+00:00"))


def plan_artifacts(http: Http, repo: str, plan: Plan, min_age_hours: int) -> None:
    artifacts = collect(http, f"/repos/{repo}/actions/artifacts", plan, "artifacts")
    if artifacts is None:
        print("\n=== Workflow artifacts: unreadable, skipped ===")
        return
    live = [a for a in artifacts if not a["expired"]]
    live.sort(key=lambda a: a["created_at"], reverse=True)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=min_age_hours)

    print(
        f"\n=== Workflow artifacts ({len(artifacts)} total, "
        f"{len(live)} unexpired, {sum(a['size_in_bytes'] for a in live) / 1e9:.2f} GB; "
        f"anything newer than {min_age_hours} h is left alone) ==="
    )

    seen: dict[str, int] = {}
    freed = 0
    too_young = 0
    for artifact in live:
        name = artifact["name"]
        budget = KEEP_NEWEST_ARTIFACTS.get(name, 0)
        seen[name] = seen.get(name, 0) + 1
        if seen[name] <= budget:
            print(f"  KEEP    {name:<34} {artifact['size_in_bytes'] / 1e6:8.1f} MB  {artifact['created_at']}")
            continue
        if _created_at(artifact) > cutoff:
            too_young += 1
            continue
        freed += artifact["size_in_bytes"]
        plan.add(
            "artifact",
            f"{name} ({artifact['created_at']})",
            f"/repos/{repo}/actions/artifacts/{artifact['id']}",
        )

    doomed = plan.of("artifact")
    print(f"  DELETE  {len(doomed)} artifacts, reclaiming {freed / 1e9:.2f} GB")
    print(f"  (skipped {len(artifacts) - len(live)} already-expired entries, "
          f"{too_young} younger than {min_age_hours} h)")


def plan_tags(http: Http, repo: str, tags: list[str], plan: Plan) -> None:
    if not tags:
        return
    print("\n=== Git tags (explicit deletions only) ===")
    for tag in tags:
        sha = resolve_tag_commit(http, repo, tag)
        if sha is None:
            print(f"  SKIP    {tag} (no such tag)")
            continue
        print(f"  DELETE  {tag} -> {sha}")
        plan.add("tag", tag, f"/repos/{repo}/git/refs/tags/{urllib.parse.quote(tag)}")


def execute(http: Http, plan: Plan) -> None:
    print(f"\n=== Applying {len(plan.entries)} deletions ===")
    for kind, label, path in plan.entries:
        status, body = http.delete(path, packages=(kind == "package"))
        if status in (200, 202, 204):
            print(f"  deleted {kind:<8} {label}")
        else:
            message = (body or {}).get("message", "unknown error")
            print(f"  ::error::failed {kind} {label}: HTTP {status} {message}")
            plan.failures += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--keep-releases", type=int, default=2)
    parser.add_argument(
        "--keep-builds",
        type=int,
        default=2,
        help="How many of the kept releases retain their GHCR images.",
    )
    parser.add_argument(
        "--min-age-hours",
        type=int,
        default=DEFAULT_MIN_AGE_HOURS,
        help="Never delete a workflow artifact younger than this.",
    )
    parser.add_argument(
        "--delete-tag",
        action="append",
        default=[],
        help="Git tag to delete outright. Repeatable. Use only for strays.",
    )
    parser.add_argument("--skip-releases", action="store_true")
    parser.add_argument("--skip-packages", action="store_true")
    parser.add_argument("--skip-artifacts", action="store_true")
    parser.add_argument("--apply", action="store_true", help="Delete for real.")
    args = parser.parse_args()

    if not args.repo or "/" not in args.repo:
        print("::error::--repo must be owner/name", file=sys.stderr)
        return 2
    if args.keep_releases < 1 or args.keep_builds < 1:
        print("::error::--keep-releases and --keep-builds must be >= 1", file=sys.stderr)
        return 2
    if args.keep_builds > args.keep_releases:
        print("::error::--keep-builds cannot exceed --keep-releases", file=sys.stderr)
        return 2
    if args.min_age_hours < 0:
        print("::error::--min-age-hours must be >= 0", file=sys.stderr)
        return 2

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("::error::GITHUB_TOKEN is not set", file=sys.stderr)
        return 2

    owner = args.repo.split("/", 1)[0]
    http = Http(token, os.environ.get("GHCR_CLEANUP_TOKEN") or None)
    plan = Plan()

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"Retention prune for {args.repo} [{mode}]")
    print(f"  keep releases: {args.keep_releases}   keep image builds: {args.keep_builds}")

    kept: list[dict] = []
    if args.skip_releases:
        # Package keeps are derived from the newest releases, so the list is
        # still needed even when releases themselves are left alone.
        kept = sorted(
            http.paginate(f"/repos/{args.repo}/releases"),
            key=lambda r: r.get("published_at") or r["created_at"],
            reverse=True,
        )[: args.keep_releases]
        print("\n=== Releases: skipped ===")
    else:
        kept = plan_releases(http, args.repo, args.keep_releases, plan)

    if args.skip_packages:
        print("\n=== GHCR: skipped ===")
    else:
        plan_packages(http, owner, args.repo, kept, args.keep_builds, plan)

    if args.skip_artifacts:
        print("\n=== Workflow artifacts: skipped ===")
    else:
        plan_artifacts(http, args.repo, plan, args.min_age_hours)

    plan_tags(http, args.repo, args.delete_tag, plan)

    counts = {k: len(plan.of(k)) for k in ("release", "package", "artifact", "tag")}
    print(
        "\n=== Summary ==="
        f"\n  releases: {counts['release']}   packages: {counts['package']}"
        f"   artifacts: {counts['artifact']}   tags: {counts['tag']}"
    )

    if not args.apply:
        print("\nDry run — nothing deleted. Re-run with apply=true to execute.")
        return 1 if plan.failures else 0

    # A partial plan must not execute. If one scope could not be read, applying
    # the rest would delete releases while silently leaving images behind and
    # still report success — the operator would believe the whole policy ran.
    if plan.failures:
        print(
            f"\n::error::{plan.failures} scope(s) could not be planned; refusing to "
            "apply a partial prune. Fix the access problem above, or re-run with a "
            "narrower scope to prune only what is readable."
        )
        return 1

    execute(http, plan)
    if plan.failures:
        print(f"\n::error::{plan.failures} operation(s) failed")
        return 1
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
