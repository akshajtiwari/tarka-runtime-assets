#!/bin/sh
set -eu
# Only the public assets workspace is visible to the source-collection container.
docker run --rm -v "$PWD:/work" -w /work \
  -e OWNER_UID="$(id -u)" -e OWNER_GID="$(id -g)" \
  alpine:3.22.7@sha256:2e0b81d60597f449baa56dc25d355367869d2dca4cd57e866f1e2b52af3eb55f \
  sh -c 'trap '\''chown -R "$OWNER_UID:$OWNER_GID" /work/.artifacts'\'' EXIT; apk add --no-cache abuild python3 ca-certificates >/dev/null; python3 scripts/sources.py "$@"' sh "$@"
