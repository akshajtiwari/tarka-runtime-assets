# Reviewed source checkpoint — 2026-10-28

Reviewed build recipes and tests are published in the separate public repository
[akshajtiwari/tarka-runtime-assets](https://github.com/akshajtiwari/tarka-runtime-assets).
Runtime release assets are not yet published or tagged. The private application
checkout, accounts and signing keys were never mounted in build containers or
included in this repository.

## Implemented and verified

- Format 1 deterministic ZIPs: base, Python, Java, C/C++, for ARM64 and x86_64.
- Original Alpine APK signatures, installed metadata and exact versions verified.
- Immutable base/optional overlays and identical shared optional entries enforced.
- Every final ZIP payload was extracted with its declared size and SHA-256 checked.
- ARM64: 344 native ELF files checked; x86_64: 348. No ARM64 execution claim.
- Linux x86_64 smoke: Python/venv/pip, Git, actual gh, Java library/executable JARs,
  Maven external dependencies online/offline clean, Gradle build/run online/offline
  clean using its own runtimeClasspath, CMake/Ninja C++ multi-file builds with zlib.
- 79 exact Alpine origin source bundles: aports recipes/patches and upstream sources
  checked with `abuild fetch verify`; no remaining source-fetch failures.
- Additional Java source distributions, nine exact bundled copyleft library
  source artifacts/POMs, full original source trees/build scripts, and notices.
- Separate PRoot/talloc original sources, patches, standalone build recipe,
  cross-compilation answers, GPLv3/LGPLv3 and original/NDK notices.
- 32 focused unit tests, Python compilation and shell syntax checks pass.
- Catalog, native/Java source metadata, SHA256SUMS and explicit UPLOADS.txt generated.
- Native installer JVM tests independently parsed/verified all eight real ZIPs and
  extracted/hashed both selected ABI generations; its log is with the application
  `.artifacts/runtime-installer-work/tests.log`.
- Fresh Docker bootstrap with an empty downloads directory passed; optional pack
  packaging was intentionally skipped in that targeted bootstrap regression run.

The catalog URLs describe the intended public release location and are not live.
Changing the release repository/tag requires regenerating the catalog and checksums.
Generated files are under `.artifacts/release/`. Linux runtime proof is recorded
in `.artifacts/smoke-linux-proc.log`; final extraction/ELF checks are separate from
Android device acceptance. Default base passwd home is `/home/tarka` so Java
caches follow TARKA's writable home binding across generation changes.

## Release work still required

Application release work owns Android installation, interruption/recovery,
upgrade and process tests against these exact final hashes, plus actual ARM64
device execution. Native loader compilation/execution evidence belongs to the
application; these assets only copied its component recipes/patches and verified sources.
Reviewer findings are fixed: clean bootstrap creates its downloads directory;
catalog generation validates pack identity/base dependency and every actual payload;
header, mode/type, per-file and aggregate limits apply before and during extraction.
Simplification and security re-review approved these fixes. The initial Actions
[build run](https://github.com/akshajtiwari/tarka-runtime-assets/actions/runs/40681929693)
is in progress for version `2026.10.28.1`, from source commit
`d143e09572d2955953e794320752ae1958b3f157`. Both ABI jobs passed checkout, the
public-repository/version checks and unit tests, then started pack builds.
Complete Actions results and exact-hash Android acceptance remain required before
runtime publication.
No Maestro/UI screenshot applies to this standalone asset build repository.

Review source completeness and notices before public release. The Java bundle
includes original build trees in addition to Maven source JARs because Alpine's
Gradle/Maven recipes download binary distributions and do not by themselves supply
all bundled copyleft sources. Original upstream and source-package notices remain
unaltered in their archives; declared Alpine expressions are retained even when
nonstandard labels need display normalization.

The initial source commits are authored by Akshaj Tiwari. Final publication
workflow wiring, runtime publication and the matching private APK release remain
with application release work. Keep
`.artifacts/` ignored; upload only the explicit release list, never project caches.
