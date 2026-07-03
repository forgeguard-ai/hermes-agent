#!/bin/sh
# Container HEALTHCHECK probe for the published runtime image.
#
# Semantics: the health signal tracks the DASHBOARD, the one supervised
# service with a stable HTTP surface. When HERMES_DASHBOARD is not enabled
# (plain CLI / one-shot / gateway-only containers) the probe reports healthy
# unconditionally so those containers never flap to "unhealthy" for a service
# they deliberately don't run.
#
# /api/status is served unauthenticated — it is the same public readiness
# probe the desktop client uses — and the check targets loopback regardless
# of the configured bind host, so it works with the default 0.0.0.0 bind and
# never needs credentials.
set -eu

case "${HERMES_DASHBOARD:-}" in
    1|true|TRUE|True|yes|YES|Yes) ;;
    *) exit 0 ;;
esac

exec curl -fsS -o /dev/null --max-time 5 \
    "http://127.0.0.1:${HERMES_DASHBOARD_PORT:-9119}/api/status"
