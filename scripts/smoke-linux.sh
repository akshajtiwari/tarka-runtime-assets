#!/bin/sh
set -eu
# Mount only container procfs; Java uses it to resolve libraries and detect musl.
# Docker AppArmor otherwise denies this mount even with SYS_ADMIN on Ubuntu runners.
docker run --rm --cap-add=SYS_ADMIN --security-opt apparmor=unconfined \
  -v "$PWD:/work" -w /work \
  alpine:3.22.7@sha256:2e0b81d60597f449baa56dc25d355367869d2dca4cd57e866f1e2b52af3eb55f \
  sh scripts/smoke-inside.sh
