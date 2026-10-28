#!/bin/sh
set -eu
trap 'chown -R "$OWNER_UID:$OWNER_GID" /work/.artifacts' EXIT
apk upgrade --no-cache
apk add --no-cache curl python3 p11-kit-trust ca-certificates
case "$TARGET_ARCH" in
  x86_64) checksum=57e364a241bab0699cd8a760c0fd7b270e9cbcbd3cee822cb2b07ca6d925c16c ;;
  aarch64) checksum=7e9b34ff3304381909e566e2c93de450664ccc724191261423974fc121c11623 ;;
  *) exit 1 ;;
esac
mkdir -p /work/.artifacts/downloads
archive="/work/.artifacts/downloads/minirootfs-$TARGET_ARCH.tar.gz"
if [ ! -f "$archive" ]; then
  curl -fL --retry 2 "https://dl-cdn.alpinelinux.org/alpine/v3.22/releases/$TARGET_ARCH/alpine-minirootfs-3.22.7-$TARGET_ARCH.tar.gz" -o "$archive.part"
  mv "$archive.part" "$archive"
fi
printf '%s  %s\n' "$checksum" "$archive" | sha256sum -c
build="/work/.artifacts/roots/$TARGET_ARCH"
rm -rf "$build"
mkdir -p "$build/base"
tar -xzf "$archive" -C "$build/base"
# One cached index snapshot is copied to all optional roots for this ABI.
apk --root "$build/base" --arch "$TARGET_ARCH" --no-scripts upgrade -U
apk --root "$build/base" --arch "$TARGET_ARCH" --no-scripts add git github-cli ca-certificates
python3 scripts/build_packs.py "$build" "$TARGET_ARCH" "$ABI"
