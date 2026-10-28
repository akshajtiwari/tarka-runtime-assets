#!/usr/bin/env bash
# Builds APK executables from pinned sources; nothing from the private app enters the output.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${ANDROID_HOME:?Set ANDROID_HOME to the Android SDK directory}"

abi=${1:?usage: build-proot.sh arm64-v8a|x86_64}
case "$abi" in
  arm64-v8a) target=aarch64-linux-android24 ;;
  x86_64) target=x86_64-linux-android24 ;;
  *) echo "Unsupported ABI: $abi" >&2; exit 1 ;;
esac

proof_root="$PWD/.artifacts/native-loader"
ndk_bin="$ANDROID_HOME/ndk/27.1.12297006/toolchains/llvm/prebuilt/linux-x86_64/bin"
build_dir="$proof_root/build/$abi"
mkdir -p "$proof_root/downloads" "$build_dir"

fetch_source() {
  local url=$1 hash=$2 name=$3
  local archive="$proof_root/downloads/$name"
  if [ ! -f "$archive" ]; then
    curl --fail --location --retry 2 "$url" -o "$archive.part"
    printf '%s  %s\n' "$hash" "$archive.part" | sha256sum --check
    mv "$archive.part" "$archive"
  fi
  printf '%s  %s\n' "$hash" "$archive" | sha256sum --check
}

fetch_source https://github.com/termux/proot/archive/refs/tags/v5.1.107.101.tar.gz \
  41e55685788202b864647f5969a52a60408d6a6452f265919adde819afb26ef4 proot.tar.gz
fetch_source https://www.samba.org/ftp/talloc/talloc-2.5.0.tar.gz \
  912afa237510ae542a7733998eb18a12bcda35ab6729c8e2ddb43e8d0ebab007 talloc.tar.gz

# Keep builds separate: PRoot's out-of-tree make currently doubles source paths.
rm -rf "$build_dir/proot" "$build_dir/talloc"
mkdir -p "$build_dir/proot" "$build_dir/talloc"
tar -xzf "$proof_root/downloads/proot.tar.gz" --strip-components=1 -C "$build_dir/proot"
tar -xzf "$proof_root/downloads/talloc.tar.gz" --strip-components=1 -C "$build_dir/talloc"
cp native/talloc-cross.txt "$build_dir/talloc/cross-answers.txt"
(
  cd "$build_dir/talloc"
  CC="$ndk_bin/$target-clang" ./configure --prefix="$build_dir/install" \
    --disable-rpath --disable-python --cross-compile --cross-answers=cross-answers.txt
  make -j2
)
# libreplace supplies memset_explicit on Android; the shared talloc build normally links it.
objects="$build_dir/talloc/bin/default"
"$ndk_bin/llvm-ar" rcs "$build_dir/libtalloc.a" \
  "$objects/talloc.c.5.o" "$objects/lib/replace/replace.c.2.o"

# Keep the blocked syscall number intact after PRoot synthesizes its exit result.
patch -d "$build_dir/proot" -p1 < native/patches/use-sigsys-number.patch
patch -d "$build_dir/proot" -p1 < native/patches/align-loader.patch

# The pinned upstream source uses strcmp/memset without their header in this file.
sed -i '1i #include <string.h>' "$build_dir/proot/src/extension/ashmem_memfd/ashmem_memfd.c"
(
  cd "$build_dir/proot/src"
  make -j2 GIT=false CC="$ndk_bin/$target-clang" STRIP="$ndk_bin/llvm-strip" \
    OBJCOPY="$ndk_bin/llvm-objcopy" OBJDUMP="$ndk_bin/llvm-objdump" \
    PROOT_UNBUNDLE_LOADER=/unused \
    CPPFLAGS="-D_FILE_OFFSET_BITS=64 -D_GNU_SOURCE -I. -DVERSION=\\\"5.1.107.101\\\" -DARG_MAX=131072 -I$build_dir/talloc" \
    LDFLAGS="-static $build_dir/libtalloc.a -Wl,-z,noexecstack,-z,max-page-size=16384" proot
)
output="$proof_root/lib/$abi"
mkdir -p "$output" "$proof_root/licenses"
cp "$build_dir/proot/src/proot" "$output/libproot.so"
cp "$build_dir/proot/src/loader/loader" "$output/libproot-loader.so"
"$ndk_bin/llvm-strip" "$output/"*.so
cp "$build_dir/proot/COPYING" "$proof_root/licenses/proot.txt"
cp "$build_dir/talloc/LICENSE" "$proof_root/licenses/talloc.txt"
"$ndk_bin/llvm-readelf" --file-header "$output/libproot.so" | rg 'Class:|Machine:'
sha256sum "$output/"*.so
