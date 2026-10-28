# TARKA runtime assets

Public build recipes and optional Linux tool packs for TARKA on Android.
This directory contains no application source, accounts or signing material.
The APK supplies its separately maintained PRoot loader. Packs are Alpine 3.22
userspace files, installed by TARKA as an immutable filesystem generation.

| Pack | Tools |
| --- | --- |
| base | BusyBox shell, Git, the actual GitHub CLI, CA certificates |
| python | Python 3 and pip |
| java | OpenJDK 17 JDK, Maven and Gradle 8.14.1 |
| cpp | GCC/G++, Make, CMake, Ninja, zlib headers |

`arm64-v8a` and `x86_64` are separate downloads. Language packs require the exact
base release. They can be combined; conflicting overlays fail the build.

## Build and inspect

Python 3 and Docker are required. Run from this directory:

```sh
python3 -m unittest discover -s tests -v
PACK_VERSION=2026.10.28.1 scripts/build.sh x86_64
PACK_VERSION=2026.10.28.1 scripts/build.sh arm64-v8a
python3 scripts/verify_packs.py x86_64
python3 scripts/verify_packs.py arm64-v8a
python3 scripts/check_elf.py x86_64
python3 scripts/check_elf.py arm64-v8a
scripts/smoke-linux.sh
scripts/sources.sh .artifacts/release/manifests-*.json
python3 scripts/native_sources.py
python3 scripts/java_sources.py
python3 scripts/licenses.py .artifacts/release/manifests-*.json
python3 scripts/catalog.py https://github.com/OWNER/REPOSITORY/releases/download/VERSION
python3 scripts/release_files.py --stage
```

Builds use a digest-pinned Alpine builder and checksum-pinned minirootfs.
Every component APK is signature-verified with target rootfs Alpine keys;
its exact version, immutable source commit, download URL and SHA-256 are recorded.
The selected v3.22 package index changes over time: a new build must receive a new
release version. Never replace a published artifact in place. Retain original
verified APK inputs if exact binary reproduction is needed after CDN retirement.

The public [Actions workflow](docs/ACTIONS.md) runs the same steps and records
the source revision in its review artifact. Generated outputs and caches live under `.artifacts/`. Docker sees only this
assets directory. It never mounts the private application checkout.

## Runtime constraints

TARKA binds writable project folders and `/home/tarka` outside the pack generation.
Use `HOME=/home/tarka` and `JAVA_HOME=/usr/lib/jvm/java-17-openjdk`. Caches, accounts,
GitHub tokens and project files must never be baked into a pack. Android supplies
network resolver configuration separately. There is no SSH service or Android APK
compiler in these packs. General-purpose APK package upgrades are unsupported:
the mutable APK database is omitted and optional packs install through TARKA.

Post-install scripts are disabled for cross-architecture builds. The builder
explicitly generates the portable Java truststore from the matching CA bundle.
The root passwd home is `/home/tarka`, so Java, Maven and Gradle use the writable
Android home binding for caches even though Java ignores the `HOME` variable.
Gradle's verified payload is extracted without Alpine's OpenJDK 21 dependency;
Gradle runs with Java 17. The BusyBox `strings` symlink is omitted from base so
GNU binutils can provide it in the C/C++ pack; `busybox strings` still works.

## Sources, licenses and release gate

Each source ZIP contains the exact aports recipe, patches and checksum-verified
upstream archives, with provenance. Java distribution source archives, exact
Maven Central source artifacts and full upstream source trees/build scripts for
bundled copyleft Java libraries are supplied in an additional archive. License texts and declared expressions are
bundled separately; original component copyright notices remain in the source
archives. Corresponding source is delivered under each component's own terms.
Standalone APK loader sources, patches, cross-compilation instructions and notices
are bundled from [native/](native/NOTICE.md), separately from the Linux packs.
No source archive may be replaced with a homepage link. The catalog refuses to
build while required sources are missing or downloads failed. PRoot/talloc
sources and notices accompany the catalog's separate `nativeSources` record.

All archives upload as flat release assets, including the source ZIPs. Publish
only after reviewing source completeness, licenses, pack verification and the
Android upgrade/runtime evidence. Container execution and ARM64 ELF inspection
alone do not establish Android compatibility. Current verification and remaining
work are recorded in [docs/STATUS.md](docs/STATUS.md).
