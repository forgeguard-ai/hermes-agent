# shellcheck shell=sh
# Hermes CLI image environment for login shells (sourced, not executed — no
# shebang on purpose; profile.d fragments run in the login shell itself).
#
# distrobox enter starts a login shell that does NOT inherit the image's ENV
# instructions, so everything an interactive user needs is exported here.
# /etc/profile.d is the documented place distrobox surfaces per-image setup.

# Playwright browsers are baked into the sealed install tree at build time.
export PLAYWRIGHT_BROWSERS_PATH=/opt/hermes/.playwright

# The install tree (/opt/hermes) is root-owned and read-only; opt-in backend
# SDKs lazy-install into the user's own home instead, which distrobox
# bind-mounts from the host so installs survive container recreation.
export HERMES_LAZY_INSTALL_TARGET="${HERMES_LAZY_INSTALL_TARGET:-$HOME/.hermes/lazy-packages}"

# /usr/local/bin/hermes (the launcher shim) is already on PATH; the venv bin
# dir is appended LAST so venv tooling is reachable without shadowing the
# distro's own python/pip for general use.
case ":$PATH:" in
    *:/opt/hermes/.venv/bin:*) ;;
    *) PATH="$PATH:/opt/hermes/.venv/bin" ;;
esac
export PATH
