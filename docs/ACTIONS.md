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
APKBUILD containers. The workflow requires the repository to be public and grants
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
