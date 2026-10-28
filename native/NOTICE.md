# PRoot and talloc

The APK runs PRoot as a separate executable with its bundled ELF loader.
PRoot 5.1.107.101 is available under GPL-2.0-or-later. This distribution of
PRoot statically linked with talloc 2.5.0 uses GPL version 3, consistent with
PRoot's permission to use a later GPL version. Talloc is LGPL-3.0-or-later.
The original notices, full GPLv3 and LGPLv3 texts are included here. The NDK
runtime and toolchain notices are retained for the static Android build inputs.

The corresponding-source ZIP contains exact original source archives, pinned
hashes, our patches, cross-compilation answers, and the standalone build recipe.
The source archives retain the upstream copyright notices. No TARKA application
source is included or needed to build these separate executables.

Install Android NDK 27.1.12297006 in an Android SDK, then set ANDROID_HOME to that
SDK directory. On Linux with Python 3, GNU Make, patch, tar, curl and ripgrep:

```sh
native/build-proot.sh arm64-v8a
native/build-proot.sh x86_64
```

The recipe targets Android API 24, uses static linking and a maximum ELF load
page size of 16384. It builds the separate loader from the same PRoot sources.
The SIGSYS patch preserves the real blocked syscall number; the loader patch
supports 16 KB alignment. The recipe also adds a missing upstream string.h include.
Outputs are in `.artifacts/native-loader/lib/<ABI>/`. Compiling both ABIs does
not establish Android execution compatibility; release device evidence is separate.
