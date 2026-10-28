#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
abi=${1:?usage: build.sh x86_64|arm64-v8a}
case "$abi" in
  x86_64) arch=x86_64 ;;
  arm64-v8a) arch=aarch64 ;;
  *) echo "Unsupported ABI: $abi" >&2; exit 1 ;;
esac
mkdir -p .artifacts
# Only the public-assets working folder enters this container.
docker run --rm -v "$PWD:/work" -w /work \
  -e PACK_VERSION="${PACK_VERSION:-2026.10.28.1}" -e ABI="$abi" -e TARGET_ARCH="$arch" -e OWNER_UID="$(id -u)" -e OWNER_GID="$(id -g)" \
  alpine@sha256:2e0b81d60597f449baa56dc25d355367869d2dca4cd57e866f1e2b52af3eb55f \
  sh scripts/build-inside.sh
