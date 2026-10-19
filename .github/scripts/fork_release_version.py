#!/usr/bin/env python3
"""Compute the fork's release version and render its release notes.

Used by ``.github/workflows/release-on-merge.yml``. Kept as a script (rather
than inline shell) so the version rules are unit-tested — see
``tests/fork/test_release_version.py``.

Two modes, chosen by the upstream base recorded in ``FORK_UPSTREAM_BASE``:

``upstream-release``
    The base is a plain upstream semver release such as ``v0.22.2``. The
    release is ``<base without v>-forgeguard.<N>`` (tag ``v0.22.2-forgeguard.1``),
    N starting at 1 for each upstream release and counting up from the
    highest ``v<base>-forgeguard.<n>`` tag that already exists on the remote.
    The version files (``pyproject.toml`` and friends) are not read: from the
    sync to upstream's release-based versioning onward they hold ``0.0.0`` and
    the real version comes from the build-time install stamp.

``legacy``
    Anything else — notably the calendar-shaped bases (``v2026.8.31``) the
    fork tracked before it synced to upstream's semver releases. The release
    is the ``pyproject.toml`` version (``v0.21.1``); a re-cut of an
    already-released version gets ``-forgeguard.<n>`` with the plain tag
    counted as cut 1. This is the behaviour the workflow had before the
    upstream-release mode existed, unchanged.

Either way the script refuses to produce an empty version or a ``0.0.0`` one.

``FORK_UPSTREAM_COMMIT`` (optional) names the exact upstream commit the fork
merged. It matters when an upstream release tag is not on upstream ``main``
and the sync merges a tree-identical commit instead; the release notes show
it next to the base.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

# A plain upstream semver release tag: v<major>.<minor>.<patch>, no
# pre-release or build suffix.
_SEMVER_TAG = re.compile(r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
# Calendar-shaped bases start with a year; anything from here up is treated as
# a date, not a semver major.
_CALENDAR_MAJOR_FLOOR = 2000
_FORGEGUARD_SUFFIX = re.compile(r"-forgeguard\.([0-9]+)$")
_COMMIT = re.compile(r"^[0-9a-f]{7,40}$")

NOTES_PLACEHOLDER_DIGEST = "(recorded when the runtime image is published)"
UPSTREAM_REPO_URL = "https://github.com/NousResearch/hermes-agent"


class ReleaseVersionError(Exception):
    """The inputs cannot produce a releasable version."""


@dataclass(frozen=True)
class ReleaseVersion:
    mode: str
    version: str
    base_tag: str
    hermes_version: str
    upstream_commit: str

    def outputs(self) -> dict[str, str]:
        return {
            "mode": self.mode,
            "version": self.version,
            "base_tag": self.base_tag,
            "hermes_version": self.hermes_version,
            "upstream_commit": self.upstream_commit,
        }


def upstream_release(base_tag: str) -> str | None:
    """Return ``0.22.2`` for an upstream semver release base, else None."""
    match = _SEMVER_TAG.match(base_tag)
    if not match:
        return None
    if int(match.group(1)) >= _CALENDAR_MAJOR_FLOOR:
        return None
    return base_tag[1:]


def normalise_tags(lines: list[str]) -> list[str]:
    """Accept bare tag names or ``git ls-remote --tags`` output."""
    tags = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        ref = line.split()[-1]
        if ref.endswith("^{}"):
            ref = ref[: -len("^{}")]
        if ref.startswith("refs/tags/"):
            ref = ref[len("refs/tags/") :]
        tags.append(ref)
    return tags


def highest_cut(tags: list[str], base: str, *, plain_counts_as_one: bool) -> int:
    """Highest ``-forgeguard.<n>`` cut of ``base`` among ``tags`` (0 if none).

    Only tags whose final segment is exactly ``-forgeguard.<digits>`` count, so
    an odd hand-made tag such as ``<base>-forgeguard.5-hotfix1`` is skipped
    rather than blocking every future release.
    """
    highest = 0
    prefix = base + "-forgeguard."
    for tag in tags:
        if tag == base:
            if plain_counts_as_one:
                highest = max(highest, 1)
            continue
        if not tag.startswith(prefix):
            continue
        match = _FORGEGUARD_SUFFIX.search(tag)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest


def pyproject_version(pyproject: Path) -> str:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return str(data.get("project", {}).get("version", "")).strip()


def read_upstream_commit(path: Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    value = path.read_text(encoding="utf-8").strip().lower()
    if not value:
        return ""
    if not _COMMIT.match(value):
        raise ReleaseVersionError(
            f"{path.name} must hold one upstream commit SHA (7-40 hex characters); got {value!r}"
        )
    return value


def _is_zero(version: str) -> bool:
    core = version[1:] if version.startswith("v") else version
    core = re.split(r"[-+]", core, maxsplit=1)[0]
    return core in {"", "0", "0.0", "0.0.0"}


def compute(
    *,
    base_tag: str,
    pyproject: Path,
    remote_tags: list[str],
    release_tags: list[str],
    upstream_commit: str = "",
) -> ReleaseVersion:
    """Compute the release version.

    ``remote_tags`` are the tags on the remote (upstream-release mode);
    ``release_tags`` are the GitHub Release tag names (legacy mode, as before).
    """
    base_tag = base_tag.strip()
    if not base_tag:
        raise ReleaseVersionError("no upstream base: FORK_UPSTREAM_BASE is missing or empty")

    product = upstream_release(base_tag)
    if product is not None:
        if _is_zero(product):
            raise ReleaseVersionError(f"FORK_UPSTREAM_BASE is {base_tag}; refusing to release 0.0.0")
        cut = highest_cut(normalise_tags(remote_tags), base_tag, plain_counts_as_one=False)
        version = f"{base_tag}-forgeguard.{cut + 1}"
        return ReleaseVersion("upstream-release", version, base_tag, product, upstream_commit)

    hermes_version = pyproject_version(pyproject)
    if _is_zero(hermes_version):
        raise ReleaseVersionError(
            f"pyproject.toml version is {hermes_version or 'empty'!r} and FORK_UPSTREAM_BASE "
            f"({base_tag}) is not a plain upstream release such as v0.22.2; refusing to release. "
            "Record the upstream release in FORK_UPSTREAM_BASE."
        )
    semver_base = f"v{hermes_version}"
    cut = highest_cut(normalise_tags(release_tags), semver_base, plain_counts_as_one=True)
    version = semver_base if cut == 0 else f"{semver_base}-forgeguard.{cut + 1}"
    return ReleaseVersion("legacy", version, base_tag, hermes_version, upstream_commit)


def render_notes(
    template: str,
    *,
    version: str,
    base_tag: str,
    hermes_version: str,
    upstream_commit: str = "",
    pr_number: str = "",
    runtime_digest: str = "",
    image: str = "ghcr.io/forgeguard-ai/hermes-agent",
) -> str:
    if pr_number:
        origin = f"Fork release automatically built on merge of #{pr_number} into `main`."
    else:
        origin = "Fork release built by a manual run of the release workflow on `main`."
    if upstream_commit:
        commit = f" ([`{upstream_commit[:10]}`]({UPSTREAM_REPO_URL}/commit/{upstream_commit}))"
    else:
        commit = ""
    if runtime_digest:
        digest = f"`{runtime_digest}` (pin with `docker pull {image}@{runtime_digest}`)"
    else:
        digest = NOTES_PLACEHOLDER_DIGEST
    replacements = {
        "__ORIGIN__": origin,
        "__VERSION__": version,
        "__BASE_TAG__": base_tag,
        "__HERMES_VERSION__": hermes_version,
        "__UPSTREAM_COMMIT__": commit,
        "__RUNTIME_DIGEST__": digest,
        "__IMAGE__": image,
    }
    notes = template
    for token, value in replacements.items():
        notes = notes.replace(token, value)
    return notes


def _read_lines(path: Path | None) -> list[str]:
    if path is None or not path.is_file():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _cmd_version(args: argparse.Namespace) -> int:
    try:
        result = compute(
            base_tag=args.base_tag,
            pyproject=args.pyproject,
            remote_tags=_read_lines(args.remote_tags),
            release_tags=_read_lines(args.release_tags),
            upstream_commit=read_upstream_commit(args.upstream_commit_file),
        )
    except ReleaseVersionError as exc:
        print(f"::error::{exc}")
        return 1
    lines = [f"{key}={value}" for key, value in result.outputs().items()]
    if args.output:
        with open(args.output, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    if result.mode == "legacy" and result.version != f"v{result.hermes_version}":
        print(
            f"::notice::Product version v{result.hermes_version} already released — "
            f"cutting re-release {result.version}."
        )
    print(
        f"::notice::Computed release version: {result.version} ({result.mode} mode, "
        f"upstream base {result.base_tag}, Hermes Agent v{result.hermes_version})"
    )
    if result.mode == "upstream-release" and not result.upstream_commit:
        print(
            "::warning::FORK_UPSTREAM_COMMIT is missing; the release notes will name the "
            "upstream release without the exact upstream commit."
        )
    return 0


def _cmd_notes(args: argparse.Namespace) -> int:
    notes = render_notes(
        args.template.read_text(encoding="utf-8"),
        version=args.version,
        base_tag=args.base_tag,
        hermes_version=args.hermes_version,
        upstream_commit=args.upstream_commit,
        pr_number=args.pr,
        runtime_digest=args.runtime_digest,
        image=args.image,
    )
    if args.output:
        Path(args.output).write_text(notes, encoding="utf-8")
    else:
        sys.stdout.write(notes)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    ver = sub.add_parser("version", help="compute the release version")
    ver.add_argument("--base-tag", required=True, help="upstream base (contents of FORK_UPSTREAM_BASE)")
    ver.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    ver.add_argument("--upstream-commit-file", type=Path, default=Path("FORK_UPSTREAM_COMMIT"))
    ver.add_argument("--remote-tags", type=Path, help="tag names or `git ls-remote --tags` output")
    ver.add_argument("--release-tags", type=Path, help="GitHub Release tag names, one per line")
    ver.add_argument("--output", help="append key=value outputs here (e.g. $GITHUB_OUTPUT)")
    ver.set_defaults(func=_cmd_version)

    notes = sub.add_parser("notes", help="render the release notes")
    notes.add_argument("--template", type=Path, required=True)
    notes.add_argument("--version", required=True)
    notes.add_argument("--base-tag", required=True)
    notes.add_argument("--hermes-version", required=True)
    notes.add_argument("--upstream-commit", default="")
    notes.add_argument("--pr", default="")
    notes.add_argument("--runtime-digest", default="")
    notes.add_argument("--image", default="ghcr.io/forgeguard-ai/hermes-agent")
    notes.add_argument("--output")
    notes.set_defaults(func=_cmd_notes)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
