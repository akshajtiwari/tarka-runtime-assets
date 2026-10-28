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
- 42 focused unit tests, Python compilation and shell syntax checks pass.
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
Simplification and security re-review approved the pack validation fixes. The initial
[Actions run](https://github.com/akshajtiwari/tarka-runtime-assets/actions/runs/40681929693)
built both ABI packs successfully, then failed because Docker AppArmor denied the
smoke container's procfs mount. The smoke now scopes AppArmor relaxation to that
isolated container and exits immediately if mounting fails. Its full local runtime
smoke and mount-failure regression test pass. The corrected
[Actions run](https://github.com/akshajtiwari/tarka-runtime-assets/actions/runs/40685892432),
from source commit `028f12c8f655c08589896ac965fd77b5b8092cae`, passed both ABI
build jobs and the complete payload/ELF/toolchain smoke step on the hosted runner.
That run collected all Alpine and Java sources, then failed with HTTP 504 while
fetching a pinned native source. Samba's talloc server also timed out locally.
Native source fetching now has bounded timeouts/retries and a BLFS mirror whose
talloc archive matches the existing SHA-256 exactly. Downloads are verified before
atomic cache installation; failed or mismatched downloads leave no partial cache.
A fresh download of both native sources passed, including the mirror fallback.
The native source bundle/catalog change to record that mirror; runtime ZIPs do not.
The reviewed fix is source commit `08291e4fae8fadb2fc84d80563f37866037851e2`.
Its [Actions run](https://github.com/akshajtiwari/tarka-runtime-assets/actions/runs/40692292015)
passed every job, including source collection, complete catalog and review artifact
upload. Downloading its actual runtime artifacts proved six ZIPs match the local
catalog exactly. Both Java ZIPs differed only in generated JKS entry creation dates
and the resulting integrity footer; all 118 aliases, certificate types and
certificate bytes were identical.

The builder now fixes only those creation dates and recomputes the standard JKS
integrity footer. It verifies the original footer, rejects private-key entries and
malformed/truncated stores, and preserves certificate bytes and ordering. Four real
stores from independent local/Actions builds normalize to identical bytes across
both ABIs. Java-only rebuilds and strict catalog validation pass; the six other ZIPs
remain unchanged. Fresh-root Java17 keytool inspection and full online/offline
Maven/Gradle toolchain smoke pass with the normalized truststore.
No release or tag has been created. A new Actions comparison and exact-hash Android
acceptance remain required before
runtime publication.
The normalized builder is source commit `5ac272a3066cef0e9cf480d08630305bb0c1467f`;
its [Actions run](https://github.com/akshajtiwari/tarka-runtime-assets/actions/runs/40694786441)
has been dispatched for the same unpublished version.
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
