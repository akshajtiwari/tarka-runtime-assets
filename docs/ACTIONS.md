# Runtime asset builds in GitHub Actions

The prepared [build workflow](../.github/workflows/build-assets.yml) accepts an
immutable pack version through `workflow_dispatch`. It builds both ABI outputs,
checks payloads and native ELF architectures, exercises the x86_64 toolchains,
collects corresponding sources/notices and produces a flat, checksummed
`runtime-release-<version>` artifact for review.

The workflow records the public source commit and build run in `build-source.json`.
All action references are pinned to complete commit hashes. Checkout explicitly
uses `persist-credentials: false`; source-fetch containers receive only the public
assets checkout and explicit build variables. No GitHub token, runner home, SDK,
Docker socket, private application checkout or signing material is mounted into
APKBUILD containers. The Linux smoke mounts fresh container procfs with
`SYS_ADMIN` and container-scoped `apparmor=unconfined`; Ubuntu runner AppArmor
otherwise rejects this mount. Host procfs and host PID namespaces are not shared.
The inner shell exits immediately on a failed mount. The workflow requires the repository to be public and grants
only `contents: read`.

Action versions were checked against the upstream action repositories:
[checkout](https://github.com/actions/checkout),
[upload-artifact](https://github.com/actions/upload-artifact),
[download-artifact](https://github.com/actions/download-artifact).
The credential setting follows the upstream [checkout instructions](https://github.com/actions/checkout#usage).

This workflow has been validated locally with actionlint 1.7.12 and shell syntax
checks. The initial run is tracked in [STATUS.md](STATUS.md).
Final publication uses the reviewed candidate hashes and matching Android acceptance
evidence through application release work. A rerun against a changed Alpine package
index requires a new version; published artifacts must remain immutable.

## Manual tool-pack candidates

The prepared [candidate workflow](../.github/workflows/publish-candidate.yml) takes
`run_id` and `version`. Dispatch follows exact-build hash review and x86_64 Android
toolchain acceptance. This workflow has not been dispatched yet.

Its verification job has only `actions: read` and `contents: read`. It accepts a
successful manual `build-assets.yml` run on `main` in this same public repository,
then downloads that run's unique versioned artifact by immutable artifact ID.
It requires the complete flat allowlist, every SHA256SUMS entry, catalog identities,
source/license references and exact build provenance to agree.

The separate publication job has only `contents: write`. It downloads the verified
artifact and repeats its file checks. Checkout credentials are not persisted.
Neither job runs Docker or executes any downloaded toolchain or source payload.
The workflow refuses existing tags/releases and creates the tag atomically at the
selected build commit, even if later documentation commits exist on `main`.
It uploads into a draft, then publishes a prerelease with `latest=false`.
Titles and file-backed notes label it a tool-pack candidate with ARM execution
unverified; finished application acceptance remains separate.

A failed upload or API call stops publication. Any newly created tag/draft is
retained for owner inspection; reruns refuse it instead of overwriting or deleting
it. Unit tests, local real-payload validation and actionlint cover the prepared
workflow. Live publication permissions and uploads still require the first run.
