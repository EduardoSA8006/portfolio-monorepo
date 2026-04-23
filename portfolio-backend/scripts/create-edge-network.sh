#!/usr/bin/env bash
# Creates the shared `edge` Docker network used by the Traefik stack and
# the backend. Idempotent: safe to rerun.
#
# The subnet 172.28.0.0/16 is fixed so TRUSTED_PROXY_CIDRS in the API's .env
# can pin validation to it. If you must change the subnet, also update
# TRUSTED_PROXY_CIDRS in /srv/portfolio-backend/.env.

set -euo pipefail

SUBNET="${EDGE_SUBNET:-172.28.0.0/16}"
NAME="edge"

if docker network inspect "$NAME" >/dev/null 2>&1; then
    actual_subnet=$(
        docker network inspect "$NAME" \
            --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
    )
    if [ "$actual_subnet" != "$SUBNET" ]; then
        echo "WARN: network '$NAME' exists with subnet $actual_subnet (expected $SUBNET)." >&2
        echo "      Update TRUSTED_PROXY_CIDRS to match, or recreate the network." >&2
    else
        echo "OK: network '$NAME' already exists with subnet $SUBNET."
    fi
    exit 0
fi

echo "Creating Docker network '$NAME' with subnet $SUBNET..."
docker network create \
    --driver bridge \
    --subnet "$SUBNET" \
    "$NAME"
echo "Done."
