#!/usr/bin/env python3
"""Validate the ForgeGuard documentation overlay.

Fork-owned validator for the ForgeGuard README/docs standard. It checks the
`.forgeguard/docs.yml` manifest, the published `docs/site/` tree (front matter,
links, images, anchors, path-escapes, symlinks), the maintainer/publication
boundary, the banner asset, and the root `README.md` contract.

It validates only the ForgeGuard overlay — it deliberately does not touch the
upstream `website/docs/` Docusaurus tree, which has its own checks.

Runtime dependencies: Python 3.11+ and PyYAML (already used by the repo's
docs-site checks). No other third-party packages.

Usage:
    python scripts/docs/validate_docs.py [--repo-root PATH]

Exit code 0 if all checks pass, 1 otherwise.
"""

from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

import yaml

# --- Contract constants -----------------------------------------------------

MANIFEST_PATH = ".forgeguard/docs.yml"
SITE_ROOT = "docs/site"
MAINTAINERS_ROOT = "docs/maintainers"
ENTRYPOINT = "index.md"
BANNER_PATH = "docs/site/assets/repository/banner-dark.png"
BANNER_DIMS = (2172, 724)

ALLOWED_STATUS = {"stable", "beta", "experimental", "deprecated"}
ALLOWED_KIND = {"original", "maintained-fork"}

ARTIFACT_NAMESPACE = "ghcr.io/forgeguard-ai/hermes-agent"
UPSTREAM_REPO = "NousResearch/hermes-agent"

# Old fork-doc paths that must not carry canonical content any more (only a
# single redirect stub README is allowed under docs/forgeguard-fork/).
LEGACY_FORK_DIR = "docs/forgeguard-fork"
LEGACY_ALLOWED = {"docs/forgeguard-fork/README.md"}

LINK_RE = re.compile(r"(?<!\\)\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


class Reporter:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def slugify(heading: str) -> str:
    """GitHub-style heading anchor slug.

    Lowercase, strip inline code backticks, drop characters that are not
    alphanumeric / space / hyphen, then convert spaces to hyphens. This matches
    GitHub's rendered-anchor behaviour closely enough for internal link checks.
    """
    text = heading.strip().lower()
    text = text.replace("`", "")
    # Drop markdown link syntax, keeping the link text.
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[^a-z0-9 \-]", "", text)
    text = text.replace(" ", "-")
    return text


def split_front_matter(text: str) -> tuple[dict | None, int]:
    """Return (front_matter_dict_or_None, body_start_line_index)."""
    if not text.startswith("---"):
        return None, 0
    lines = text.splitlines()
    # find closing '---'
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm_text = "\n".join(lines[1:i])
            try:
                data = yaml.safe_load(fm_text)
            except yaml.YAMLError as exc:  # pragma: no cover - defensive
                raise ValueError(f"invalid YAML front matter: {exc}") from exc
            if data is None:
                data = {}
            if not isinstance(data, dict):
                raise ValueError("front matter is not a mapping")
            return data, i + 1
    return None, 0


def collect_headings(text: str) -> set[str]:
    anchors: set[str] = set()
    in_code = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = HEADING_RE.match(line)
        if m:
            anchors.add(slugify(m.group(2)))
    return anchors


def is_external(target: str) -> bool:
    return bool(re.match(r"^(https?:|mailto:|tel:)", target, re.IGNORECASE))


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as fh:
        header = fh.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG file")
    width, height = struct.unpack(">II", header[16:24])
    return width, height


# --- Individual checks ------------------------------------------------------


def check_manifest(root: Path, rep: Reporter) -> None:
    path = root / MANIFEST_PATH
    if not path.is_file():
        rep.error(f"{MANIFEST_PATH}: manifest missing")
        return
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        rep.error(f"{MANIFEST_PATH}: invalid YAML: {exc}")
        return
    if not isinstance(data, dict):
        rep.error(f"{MANIFEST_PATH}: top level must be a mapping")
        return

    def req(mapping: dict, key: str, where: str):
        if key not in mapping or mapping[key] in (None, ""):
            rep.error(f"{MANIFEST_PATH}: missing '{where}{key}'")
            return None
        return mapping[key]

    if data.get("version") != 1:
        rep.error(f"{MANIFEST_PATH}: 'version' must be 1")
    if data.get("enabled") is not True:
        rep.error(f"{MANIFEST_PATH}: 'enabled' must be true")

    project = data.get("project")
    slug = None
    if not isinstance(project, dict):
        rep.error(f"{MANIFEST_PATH}: 'project' section missing")
    else:
        slug = req(project, "slug", "project.")
        req(project, "title", "project.")
        req(project, "summary", "project.")
        kind = req(project, "kind", "project.")
        if kind is not None and kind not in ALLOWED_KIND:
            rep.error(f"{MANIFEST_PATH}: project.kind '{kind}' not in {sorted(ALLOWED_KIND)}")
        if slug is not None and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(slug)):
            rep.error(f"{MANIFEST_PATH}: project.slug '{slug}' is not a valid slug")

    repo = data.get("repository")
    if not isinstance(repo, dict):
        rep.error(f"{MANIFEST_PATH}: 'repository' section missing")
    else:
        req(repo, "owner", "repository.")
        req(repo, "name", "repository.")
        req(repo, "default_branch", "repository.")

    source = data.get("source")
    if not isinstance(source, dict):
        rep.error(f"{MANIFEST_PATH}: 'source' section missing")
    else:
        if source.get("content_root") != SITE_ROOT:
            rep.error(f"{MANIFEST_PATH}: source.content_root must be '{SITE_ROOT}'")
        if source.get("entrypoint") != ENTRYPOINT:
            rep.error(f"{MANIFEST_PATH}: source.entrypoint must be '{ENTRYPOINT}'")

    publishing = data.get("publishing")
    if not isinstance(publishing, dict):
        rep.error(f"{MANIFEST_PATH}: 'publishing' section missing")
    else:
        route = publishing.get("route")
        if not isinstance(route, str) or not route.startswith("/"):
            rep.error(f"{MANIFEST_PATH}: publishing.route must be an absolute path")
        elif slug is not None and f"/{slug}/" not in route + "/":
            rep.error(
                f"{MANIFEST_PATH}: publishing.route '{route}' should contain the "
                f"project slug '{slug}'"
            )
        if publishing.get("versions") not in {"releases", "default-branch", "both"}:
            rep.error(f"{MANIFEST_PATH}: publishing.versions must be releases|default-branch|both")
        if not isinstance(publishing.get("include_generated"), bool):
            rep.error(f"{MANIFEST_PATH}: publishing.include_generated must be a boolean")

    kind = project.get("kind") if isinstance(project, dict) else None
    if kind == "maintained-fork":
        upstream = data.get("upstream")
        if not isinstance(upstream, dict):
            rep.error(f"{MANIFEST_PATH}: maintained-fork requires an 'upstream' section")
        else:
            if not upstream.get("repository"):
                rep.error(f"{MANIFEST_PATH}: upstream.repository is required for maintained forks")
            if not upstream.get("tracking_policy"):
                rep.error(f"{MANIFEST_PATH}: upstream.tracking_policy is required for maintained forks")


def iter_markdown(base: Path):
    for path in sorted(base.rglob("*.md")):
        yield path


def check_symlinks(root: Path, rep: Reporter) -> None:
    site = root / SITE_ROOT
    if not site.exists():
        return
    for path in site.rglob("*"):
        if path.is_symlink():
            rel = path.relative_to(root)
            rep.error(f"{rel}: symlinks are not allowed under {SITE_ROOT}")


def check_site(root: Path, rep: Reporter) -> None:
    site = root / SITE_ROOT
    if not (site / ENTRYPOINT).is_file():
        rep.error(f"{SITE_ROOT}/{ENTRYPOINT}: entrypoint missing")

    # Cache headings per markdown file for anchor resolution.
    heading_cache: dict[Path, set[str]] = {}

    def headings_for(path: Path) -> set[str]:
        if path not in heading_cache:
            try:
                heading_cache[path] = collect_headings(path.read_text(encoding="utf-8"))
            except OSError:
                heading_cache[path] = set()
        return heading_cache[path]

    for md in iter_markdown(site):
        rel = md.relative_to(root)
        text = md.read_text(encoding="utf-8")

        # Front matter
        try:
            fm, _ = split_front_matter(text)
        except ValueError as exc:
            rep.error(f"{rel}: {exc}")
            fm = None
        if fm is None:
            rep.error(f"{rel}: missing YAML front matter (--- delimited block)")
        else:
            title = fm.get("title")
            if not isinstance(title, str) or not title.strip():
                rep.error(f"{rel}: front matter 'title' must be a non-empty string")
            desc = fm.get("description")
            if not isinstance(desc, str) or not desc.strip():
                rep.error(f"{rel}: front matter 'description' must be a non-empty string")
            order = fm.get("order")
            if not isinstance(order, int) or isinstance(order, bool):
                rep.error(f"{rel}: front matter 'order' must be an integer")
            status = fm.get("status")
            if status not in ALLOWED_STATUS:
                rep.error(f"{rel}: front matter 'status' must be one of {sorted(ALLOWED_STATUS)}")

        # Links and images
        for target in LINK_RE.findall(text) + IMAGE_RE.findall(text):
            _check_target(root, site, md, target, rep, headings_for, require_within=True)


def check_maintainers(root: Path, rep: Reporter) -> None:
    base = root / MAINTAINERS_ROOT
    if not base.exists():
        return
    for md in iter_markdown(base):
        text = md.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text) + IMAGE_RE.findall(text):
            # Maintainer pages may link outside their tree (into docs/site or repo
            # root); only check that relative targets resolve on disk.
            _check_target(root, base, md, target, rep, headings_for=None, require_within=False)


def _check_target(root, within_root, md, target, rep, headings_for, require_within):
    rel = md.relative_to(root)
    target = target.strip()
    if not target or is_external(target):
        return
    if target.startswith("#"):
        anchor = target[1:]
        if headings_for is not None and anchor:
            if slugify_anchor(anchor) not in headings_for(md):
                rep.error(f"{rel}: broken in-page anchor '#{anchor}'")
        return

    path_part, _, anchor = target.partition("#")
    if not path_part:
        return
    resolved = (md.parent / path_part).resolve()

    # Path-escape check for published pages.
    if require_within:
        site_resolved = (root / SITE_ROOT).resolve()
        try:
            resolved.relative_to(site_resolved)
        except ValueError:
            rep.error(
                f"{rel}: relative link '{target}' escapes the publication root "
                f"({SITE_ROOT}); use an absolute URL or link within {SITE_ROOT}"
            )
            return

    if not resolved.exists():
        rep.error(f"{rel}: broken relative link '{target}' (missing {path_part})")
        return

    # Anchor resolution when the target is a markdown file we can read.
    if anchor and resolved.suffix == ".md" and headings_for is not None:
        if slugify_anchor(anchor) not in headings_for(resolved):
            rep.error(f"{rel}: broken anchor '#{anchor}' in link '{target}'")


def slugify_anchor(anchor: str) -> str:
    # Anchors in links are already slug-shaped; normalise casing/spacing only.
    return anchor.strip().lower()


def check_publication_boundary(root: Path, rep: Reporter) -> None:
    """No maintainer content published under docs/site, and no duplicate
    canonical fork pages left behind in the legacy directory."""
    legacy = root / LEGACY_FORK_DIR
    if legacy.exists():
        for path in sorted(legacy.rglob("*")):
            if path.is_file():
                rel = str(path.relative_to(root))
                if rel not in LEGACY_ALLOWED:
                    rep.error(
                        f"{rel}: legacy fork-doc file should be migrated; only a "
                        f"redirect stub ({sorted(LEGACY_ALLOWED)}) may remain"
                    )

    # docs/site pages must not relative-link into docs/maintainers (that is both
    # a path escape and a user-task-requires-maintainer-page leak). The escape
    # check in check_site already catches relative links; here we also reject
    # absolute in-repo blob links into docs/maintainers from published pages.
    site = root / SITE_ROOT
    if site.exists():
        for md in iter_markdown(site):
            text = md.read_text(encoding="utf-8")
            if re.search(r"forgeguard-ai/hermes-agent/(?:blob|tree)/[^)\s]*docs/maintainers", text):
                rep.warn(
                    f"{md.relative_to(root)}: published page links into "
                    f"docs/maintainers; ensure no user task depends on it"
                )


def check_banner(root: Path, rep: Reporter) -> None:
    path = root / BANNER_PATH
    if not path.is_file():
        rep.error(f"{BANNER_PATH}: banner asset missing")
        return
    try:
        dims = png_dimensions(path)
    except ValueError as exc:
        rep.error(f"{BANNER_PATH}: {exc}")
        return
    if dims != BANNER_DIMS:
        rep.error(f"{BANNER_PATH}: banner is {dims[0]}x{dims[1]}, expected {BANNER_DIMS[0]}x{BANNER_DIMS[1]}")


def check_readme(root: Path, rep: Reporter) -> None:
    path = root / "README.md"
    if not path.is_file():
        rep.error("README.md: missing")
        return
    text = path.read_text(encoding="utf-8")

    if "docs/site/assets/repository/banner-dark.png" not in text:
        rep.error("README.md: does not reference the ForgeGuard banner asset")
    if "assets/banner.png" in text:
        rep.error("README.md: still references the old upstream banner hero (assets/banner.png)")
    if "> [!IMPORTANT]" not in text:
        rep.error("README.md: missing the compact [!IMPORTANT] fork alert")
    if "ForgeGuard maintained fork of" not in text:
        rep.error("README.md: fork alert must state 'ForgeGuard maintained fork of'")
    if "docs/site/index.md" not in text and "docs/site/" not in text:
        rep.error("README.md: missing a link into docs/site/")
    if not re.search(r"\]\(\./LICENSE\)|\]\(LICENSE\)", text):
        rep.error("README.md: missing a local LICENSE link")
    if ARTIFACT_NAMESPACE not in text:
        rep.error(f"README.md: missing the artifact namespace '{ARTIFACT_NAMESPACE}'")


def check_typo_and_namespace(root: Path, rep: Reporter) -> None:
    """No known-bad artifact-namespace typo in overlay content."""
    targets = [root / "README.md", root / MANIFEST_PATH]
    for base in (root / SITE_ROOT, root / MAINTAINERS_ROOT):
        if base.exists():
            targets.extend(iter_markdown(base))
    for path in targets:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"forgeuard", text):
            rel = path.relative_to(root)
            rep.error(f"{rel}: contains the 'forgeuard' typo (should be 'forgeguard')")
            break


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the ForgeGuard docs overlay.")
    parser.add_argument("--repo-root", default=".", help="Repository root (default: cwd)")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()

    rep = Reporter()
    check_manifest(root, rep)
    check_symlinks(root, rep)
    check_site(root, rep)
    check_maintainers(root, rep)
    check_publication_boundary(root, rep)
    check_banner(root, rep)
    check_readme(root, rep)
    check_typo_and_namespace(root, rep)

    for w in rep.warnings:
        print(f"warning: {w}")
    if rep.errors:
        for e in rep.errors:
            print(f"error: {e}")
        print(f"\nFAILED: {len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
        return 1
    print(f"OK: ForgeGuard docs overlay validated, {len(rep.warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
