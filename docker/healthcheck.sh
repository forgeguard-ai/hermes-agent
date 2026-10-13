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
# probe the desktop client uses — so the check never needs credentials. It
# targets the dashboard's effective bind host: a wildcard bind (the default
# 0.0.0.0, an empty value, or the IPv6 wildcard ::) is reached via loopback,
# but a specific-IP bind must be probed at that IP or the container would flap
# to "unhealthy" for a dashboard that is actually up.
set -eu

case "${HERMES_DASHBOARD:-}" in
    1|true|TRUE|True|yes|YES|Yes) ;;
    *) exit 0 ;;
esac

dash_host="${HERMES_DASHBOARD_HOST:-0.0.0.0}"
case "$dash_host" in
    ''|0.0.0.0|'::'|'[::]') probe_host=127.0.0.1 ;;
    *) probe_host="$dash_host" ;;
esac

# An IPv6 literal must be bracketed in the URL (http://[fd00::1]:9119/...), or
# curl rejects it and the container flaps to "unhealthy" for a live dashboard.
# Wrap a raw IPv6 probe host that is not already bracketed.
case "$probe_host" in
    *:*)
        case "$probe_host" in
            \[*) ;;
            *) probe_host="[${probe_host}]" ;;
        esac
        ;;
esac

exec curl -fsS -o /dev/null --max-time 5 \
    "http://${probe_host}:${HERMES_DASHBOARD_PORT:-9119}/api/status"
