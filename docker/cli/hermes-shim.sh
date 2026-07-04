#!/bin/sh
# Plain `hermes` launcher for the CLI image (installed at /usr/local/bin/hermes).
#
# Unlike the runtime image's exec shim (which drops root to the baked hermes
# user via s6-setuidgid), this image has no s6 and no privileged supervisor:
# distrobox runs everything as the host user it creates at first enter, and
# that user's identity must be preserved so state lands in THEIR ~/.hermes.
# So this shim only pins the interpreter to the sealed install tree's venv —
# usable by any uid, no privilege games.
exec /opt/hermes/.venv/bin/hermes "$@"
