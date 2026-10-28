#!/bin/sh
set -eu
runtime_root=${1:-/work/.artifacts/verified/x86_64}
mkdir -p "$runtime_root/workspace" "$runtime_root/home/tarka"
cp -R fixtures/. "$runtime_root/workspace/"
cp /etc/resolv.conf "$runtime_root/etc/resolv.conf"
touch "$runtime_root/dev/null"
mount -t proc -o nosuid,nodev,noexec proc "$runtime_root/proc"
trap 'umount "$runtime_root/proc"' EXIT
chroot "$runtime_root" /usr/bin/env HOME=/home/tarka JAVA_HOME=/usr/lib/jvm/java-17-openjdk PATH=/usr/lib/jvm/java-17-openjdk/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin sh /workspace/smoke.sh
