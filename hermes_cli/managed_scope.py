"""Managed scope — IT-pushed, user-immutable config & env layer.

A system-level directory (default ``/etc/hermes``, root-owned and not
user-writable) supplies ``config.yaml`` and ``.env`` values that WIN over the
user's ``~/.hermes/config.yaml`` and ``~/.hermes/.env`` on a per-leaf-key basis.

This is DISTINCT from ``hermes_cli.config.is_managed()`` / ``HERMES_MANAGED``,
which is a coarse package-manager write-lock (declarative-distro / formula
installs). That lock blocks all mutation; this layer injects specific immutable
values. The two are independent and may coexist.

Exclusive mode (``managed: {exclusive: true}`` in the managed config.yaml) goes
further: the managed directory becomes the ONLY source of config.yaml, .env,
SOUL.md, memory-provider configs, hooks and plugins, and the home copies are
neither read nor written — see the "Exclusive mode" section below.

v1 enforcement is filesystem permissions only — see
``docs/design/managed-scope.md`` §7. v1 is Linux/POSIX-first; ``get_managed_dir()``
is the single seam for adding macOS / Windows native locations later.

Attribution: do not reference any third-party product by name in this file.
"""
from __future__ import annotations

import copy
import errno
import logging
import os
import threading
from pathlib import Path
from typing import Dict, Optional

import yaml

logger = logging.getLogger(__name__)

# POSIX default. Other-platform locations are a deliberate v2 item; when added,
# they belong ONLY inside get_managed_dir().
_DEFAULT_MANAGED_DIR = Path("/etc/hermes")

_CACHE_LOCK = threading.Lock()
# path_key -> (mtime_ns, size, parsed)
_CONFIG_CACHE: Dict[str, tuple] = {}
_ENV_CACHE: Dict[str, tuple] = {}


def _under_pytest() -> bool:
    """True when running inside the test suite.

    Used to ignore the system default ``/etc/hermes`` during tests so a real
    managed scope on a developer/CI box can't leak policy into the suite. Tests
    that exercise managed scope set ``HERMES_MANAGED_DIR`` explicitly, which is
    still honored (the override path below runs before this guard takes effect).
    """
    return "PYTEST_CURRENT_TEST" in os.environ


def get_managed_dir() -> Optional[Path]:
    """Resolve the managed-scope directory, or None when no scope is present.

    Resolution (highest priority first):
      1. ``$HERMES_MANAGED_DIR`` — deployment/bootstrap path override (IT-only;
         never persisted to any .env). Honored only when set to a non-empty value
         AND the directory exists.
      2. ``/etc/hermes`` — POSIX default, when it exists. Ignored under pytest so
         a real system managed scope can't leak into the test suite.

    A non-existent directory at either tier resolves to None (no managed scope),
    which is the common case and must be cheap + side-effect-free.
    """
    override = os.environ.get("HERMES_MANAGED_DIR", "").strip()
    if override:
        p = Path(override)
        return p if p.is_dir() else None
    if _under_pytest():
        return None
    return _DEFAULT_MANAGED_DIR if _DEFAULT_MANAGED_DIR.is_dir() else None


def invalidate_managed_cache() -> None:
    """Drop cached managed config/env. For tests and post-edit reloads."""
    with _CACHE_LOCK:
        _CONFIG_CACHE.clear()
        _ENV_CACHE.clear()
        _EXCLUSIVE_CACHE.clear()


def _cached_read(path: Path, cache: Dict[str, tuple], parse):
    """Shared (mtime_ns, size)-keyed read. Returns a deepcopy of the parsed value.

    Returns ``None`` when the file is absent or fails to parse (fail-open). A
    parse failure is logged LOUDLY — the admin needs to know their policy isn't
    being applied — but never raises, so a malformed managed file can't brick
    startup.
    """
    try:
        st = path.stat()
    except OSError:
        return None  # absent
    key = (st.st_mtime_ns, st.st_size)
    path_key = str(path)
    with _CACHE_LOCK:
        hit = cache.get(path_key)
        if hit is not None and hit[:2] == key:
            return copy.deepcopy(hit[2])
    try:
        with open(path, encoding="utf-8") as f:
            parsed = parse(f)
    except Exception as exc:  # noqa: BLE001 — fail-open, but LOUD
        logger.warning(
            "managed scope: failed to parse %s: %s — IGNORING this managed file. "
            "Admin policy from this file is NOT being applied. Fix and restart.",
            path,
            exc,
        )
        return None
    with _CACHE_LOCK:
        cache[path_key] = (key[0], key[1], copy.deepcopy(parsed))
    return parsed


def load_managed_config() -> dict:
    """Parsed managed config.yaml, or {} when absent/malformed (fail-open)."""
    managed_dir = get_managed_dir()
    if managed_dir is None:
        return {}
    parsed = _cached_read(
        managed_dir / "config.yaml",
        _CONFIG_CACHE,
        lambda f: yaml.safe_load(f) or {},
    )
    return parsed if isinstance(parsed, dict) else {}


def load_managed_env() -> Dict[str, str]:
    """Parsed managed .env (KEY=VALUE), or {} when absent (fail-open)."""
    managed_dir = get_managed_dir()
    if managed_dir is None:
        return {}
    parsed = _cached_read(managed_dir / ".env", _ENV_CACHE, _parse_env)
    return parsed if isinstance(parsed, dict) else {}


def apply_managed_overlay(config: dict) -> dict:
    """Overlay administrator-pinned config values on top of an already-built dict.

    The single, shared way for any config loader that builds its own dict
    (rather than going through hermes_cli.config.load_config) to honor managed
    scope. Mirrors hermes_cli.config._load_config_impl's managed merge exactly:

      * expand the managed config's ``${VAR}`` refs against the PROCESS env only
        (never user-config-defined refs), so a user cannot shadow a managed
        literal via a ${VAR} they control;
      * normalize the managed config's root ``model`` key (a bare ``model: x/y``
        string is promoted to ``model.default``) so it can't clobber the dict
        shape callers expect;
      * leaf-level deep-merge managed ON TOP, so managed wins per-leaf while
        sibling keys stay user-controlled.

    Fail-open: returns ``config`` unchanged if no managed scope is present or on
    any error — managed scope must never break a caller's startup. Mutates and
    returns ``config`` (callers pass a dict they own).
    """
    try:
        managed = load_managed_config()
        if not managed:
            return config
        # Imported lazily to avoid an import cycle (config imports managed_scope).
        from hermes_cli.config import _deep_merge, _expand_env_vars, _normalize_root_model_keys

        managed_expanded = _normalize_root_model_keys(_expand_env_vars(managed))
        # A bare ``model: x/y`` string in the managed file must merge as
        # ``model.default`` — otherwise _deep_merge would replace the caller's
        # ``model`` dict with a string and break every ``cfg["model"]["..."]``
        # read. _normalize_root_model_keys only promotes the string when there
        # are root provider/base_url keys to migrate, so handle the bare case
        # here (matches cli.py's own string-model handling).
        if isinstance(managed_expanded.get("model"), str):
            managed_expanded = dict(managed_expanded)
            managed_expanded["model"] = {"default": managed_expanded["model"]}
        return _deep_merge(config, managed_expanded)
    except Exception:  # noqa: BLE001 — overlay must never break a caller
        logger.warning("managed scope: failed to apply config overlay", exc_info=True)
        return config


def _parse_env(f) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip().strip("\"'")
    return out


def _flatten_keys(d: dict, prefix: str = "") -> set:
    keys: set = set()
    for k, v in d.items():
        dotted = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict) and v:
            keys |= _flatten_keys(v, dotted)
        else:
            keys.add(dotted)
    return keys


def managed_config_keys() -> set:
    """Dotted leaf keys pinned by the managed config (e.g. {'model.default'})."""
    return _flatten_keys(load_managed_config())


def is_key_managed(dotted_key: str) -> bool:
    """True if the exact dotted config key is pinned by the managed layer."""
    return dotted_key in managed_config_keys()


def is_env_managed(name: str) -> bool:
    """True if the env var name is pinned by the managed .env layer."""
    return name in load_managed_env()


# ---------------------------------------------------------------------------
# Exclusive mode
# ---------------------------------------------------------------------------
#
# Opt-in via ``managed: {exclusive: true}`` in the managed config.yaml. The
# per-leaf overlay above lets an administrator pin values, but the agent can
# still rewrite everything else in its own HERMES_HOME (it runs as the uid that
# owns that directory). Exclusive mode moves the agent's *floor* files out of
# the home entirely: the managed directory (typically a read-only mount) is the
# only source for them, and the home copies are neither read nor written.
#
# Everything else in HERMES_HOME — skills/, memories/, sessions, state.db,
# auth.json, caches — is untouched and stays agent-writable, so
# self-improvement (skills, MEMORY.md / USER.md) keeps working.

# Files an administrator supplies from the managed directory in exclusive mode.
# Paths are relative both to HERMES_HOME (the ignored user copy) and to the
# managed directory (the copy that is read).
EXCLUSIVE_FILES = (
    "config.yaml",
    ".env",
    ".op.env",
    "SOUL.md",
    "gateway.json",
    "mem0.json",
    "hindsight/config.json",
)

# Directories of executable code that load ONLY from the managed directory in
# exclusive mode. The home copies are ignored — they are code the agent could
# plant for itself.
EXCLUSIVE_DIRS = ("hooks", "plugins")

# (config path, mtime_ns, size) -> bool. is_exclusive() sits on hot read paths
# (read_raw_config_readonly runs several times per agent turn), so it avoids
# the deepcopy load_managed_config() performs.
_EXCLUSIVE_CACHE: Dict[str, tuple] = {}


class ManagedScopeReadOnlyError(PermissionError):
    """A write was refused because the target is owned by the managed scope.

    A ``PermissionError`` (so an ``OSError``) on purpose: every caller that
    already handles a read-only or permission-denied config file handles this
    one too, and ``str(exc)`` is the user-facing message.
    """


def is_exclusive() -> bool:
    """True when the managed config.yaml sets ``managed.exclusive: true``.

    Only a real boolean ``true`` enables it (YAML ``true`` / ``yes`` / ``on``).
    Fail-closed to False: no managed directory, no managed config.yaml, or an
    unparseable one all mean "not exclusive", so a broken policy file degrades
    to today's overlay behaviour rather than to an agent with no config.
    """
    managed_dir = get_managed_dir()
    if managed_dir is None:
        return False
    cfg_path = managed_dir / "config.yaml"
    try:
        st = cfg_path.stat()
    except OSError:
        return False
    key = (st.st_mtime_ns, st.st_size)
    path_key = str(cfg_path)
    with _CACHE_LOCK:
        hit = _EXCLUSIVE_CACHE.get(path_key)
        if hit is not None and hit[:2] == key:
            return hit[2]
    cfg = load_managed_config()
    section = cfg.get("managed") if isinstance(cfg, dict) else None
    flag = isinstance(section, dict) and section.get("exclusive") is True
    with _CACHE_LOCK:
        _EXCLUSIVE_CACHE[path_key] = (key[0], key[1], flag)
    return flag


def exclusive_dir() -> Optional[Path]:
    """The managed directory when exclusive mode is on, else None."""
    if not is_exclusive():
        return None
    return get_managed_dir()


def _home_candidates() -> list:
    """HERMES_HOME plus the default root (profiles live under the root)."""
    homes = []
    try:
        from hermes_constants import get_default_hermes_root, get_hermes_home

        for h in (get_hermes_home(), get_default_hermes_root()):
            if h not in homes:
                homes.append(h)
    except Exception:  # noqa: BLE001 — early bootstrap
        pass
    return homes


def _relative_to(path: Path, base: Path) -> Optional[Path]:
    try:
        return Path(os.path.realpath(path)).relative_to(os.path.realpath(base))
    except (ValueError, OSError):
        return None


def _exclusive_entry(rel: Path) -> Optional[str]:
    """The EXCLUSIVE_FILES / EXCLUSIVE_DIRS entry *rel* falls under, if any."""
    rel_posix = rel.as_posix()
    if rel_posix in EXCLUSIVE_FILES:
        return rel_posix
    if rel.parts and rel.parts[0] in EXCLUSIVE_DIRS:
        return rel.parts[0]
    return None


def resolve_home_path(home, relpath: str) -> Path:
    """Where to READ an administrator-owned entry of a Hermes home.

    Exclusive mode and *relpath* in EXCLUSIVE_FILES / EXCLUSIVE_DIRS: the path
    under the managed directory (whether or not it exists — a missing managed
    SOUL.md means "no SOUL.md", never "fall back to the home copy"). Otherwise
    ``home / relpath``, unchanged.
    """
    rel = Path(relpath)
    managed = exclusive_dir()
    if managed is not None and _exclusive_entry(rel) is not None:
        return managed / rel
    return Path(home) / rel


def config_read_path(path) -> Path:
    """Redirect a user ``config.yaml`` read to the managed one in exclusive mode.

    The single seam every config.yaml reader goes through. Outside exclusive
    mode (and for any path not named ``config.yaml``) the path is returned
    unchanged. In exclusive mode every user config.yaml — the active home's,
    another profile's, an explicit gateway path — reads the managed file, so no
    loader can see a config the agent wrote for itself.
    """
    p = Path(path)
    if p.name != "config.yaml":
        return p
    managed = exclusive_dir()
    if managed is None:
        return p
    return managed / "config.yaml"


def env_read_path(path) -> Path:
    """Redirect a user ``.env`` / ``.op.env`` read to the managed one in exclusive mode."""
    p = Path(path)
    if p.name not in (".env", ".op.env"):
        return p
    managed = exclusive_dir()
    if managed is None:
        return p
    return managed / p.name


def is_under_managed_dir(path) -> bool:
    """True when *path* is the managed directory or inside it."""
    managed = get_managed_dir()
    if managed is None:
        return False
    return _relative_to(Path(path), managed) is not None


def protected_entry(path) -> Optional[str]:
    """Why *path* must not be written in exclusive mode, or None.

    Returns the administrator-owned entry name (``"config.yaml"``,
    ``"SOUL.md"``, ``"hooks"``, ...) when *path* is one of the home copies
    exclusive mode ignores, ``"managed"`` when it is inside the managed
    directory itself, and None when exclusive mode is off or the path is
    ordinary agent state (skills/, memories/, sessions, ...).
    """
    managed = exclusive_dir()
    if managed is None:
        return None
    p = Path(os.path.expanduser(str(path)))
    if _relative_to(p, managed) is not None:
        return "managed"
    for home in _home_candidates():
        rel = _relative_to(p, home)
        if rel is None:
            continue
        entry = _exclusive_entry(rel)
        if entry is not None:
            return entry
        # A named profile's own copy (<root>/profiles/<name>/config.yaml).
        if len(rel.parts) >= 3 and rel.parts[0] == "profiles":
            entry = _exclusive_entry(Path(*rel.parts[2:]))
            if entry is not None:
                return entry
    return None


def exclusive_refusal(action: str) -> str:
    """User-facing refusal for a write exclusive mode does not allow."""
    managed = get_managed_dir()
    where = str(managed) if managed is not None else "the managed scope"
    return (
        f"Cannot {action}: this agent's configuration is managed by your "
        f"administrator ({where}, exclusive mode) and cannot be changed. "
        f"Contact your administrator to modify it."
    )


def check_write_allowed(path, action: Optional[str] = None) -> None:
    """Raise ManagedScopeReadOnlyError when exclusive mode forbids writing *path*.

    No-op outside exclusive mode. Called by the shared atomic writers in
    ``utils`` and by the config / env writers, so every path that could
    rewrite a floor file refuses the same way.
    """
    entry = protected_entry(path)
    if entry is None:
        return
    raise ManagedScopeReadOnlyError(exclusive_refusal(action or f"write {path}"))


_READ_ONLY_ERRNOS = frozenset(
    e for e in (
        getattr(errno, "EROFS", None),
        getattr(errno, "EACCES", None),
        getattr(errno, "EPERM", None),
        getattr(errno, "EBUSY", None),
    ) if e is not None
)


def translate_write_error(exc: BaseException, path) -> BaseException:
    """Map a read-only-filesystem style failure on a managed path to the managed message.

    Returns a ManagedScopeReadOnlyError (to be raised ``from exc``) when *exc*
    is an EROFS / EACCES / EPERM / EBUSY ``OSError`` for a path inside the
    managed directory while exclusive mode is on; otherwise returns *exc*
    unchanged, so callers can write ``raise translate_write_error(e, p) from e``.
    """
    if (
        isinstance(exc, OSError)
        and not isinstance(exc, ManagedScopeReadOnlyError)
        and exc.errno in _READ_ONLY_ERRNOS
        and is_exclusive()
        and is_under_managed_dir(path)
    ):
        return ManagedScopeReadOnlyError(exclusive_refusal(f"write {path}"))
    return exc
