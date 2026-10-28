#!/bin/sh
set -eu
# SYS_ADMIN is used only to mount container procfs inside the disposable test root.
# Java needs procfs to resolve its libraries and detect musl correctly.
docker run --rm --cap-add=SYS_ADMIN -v "$PWD:/work" -w /work \
  alpine:3.22.7@sha256:2e0b81d60597f449baa56dc25d355367869d2dca4cd57e866f1e2b52af3eb55f \
  sh -c 'root=/work/.artifacts/verified/x86_64
    mkdir -p "$root/workspace" "$root/home/tarka"
    cp -R fixtures/. "$root/workspace/"
    cp /etc/resolv.conf "$root/etc/resolv.conf"
    touch "$root/dev/null"
    mount -t proc proc "$root/proc"
    trap '\''umount "$root/proc"'\'' EXIT
    chroot "$root" /usr/bin/env HOME=/home/tarka JAVA_HOME=/usr/lib/jvm/java-17-openjdk PATH=/usr/lib/jvm/java-17-openjdk/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin sh /workspace/smoke.sh'
