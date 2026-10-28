# Runtime pack format 1

A pack is a ZIP beginning with `manifest.json` and regular file entries below `files/`.
ZIP symlink entries, absolute entry names, `..` components and duplicate names are forbidden.
Directories and links exist only in the manifest. Hardlinks are flattened to regular files.
All modes are masked to `0777`; setuid, setgid, device nodes, sockets and FIFOs are excluded.

```json
{
  "format": 1,
  "id": "java",
  "version": "2026.10.28.1",
  "abi": "arm64-v8a",
  "baseVersion": "2026.10.28.1",
  "directories": [{ "path": "usr/lib/jvm", "mode": 493 }],
  "files": [{ "path": "usr/bin/example", "size": 10, "sha256": "hex", "mode": 493 }],
  "links": [{ "path": "usr/bin/java", "target": "../lib/jvm/java-17-openjdk/bin/java" }],
  "components": []
}
```

Paths are case-sensitive POSIX paths relative to the guest root. Link targets retain their
relative or absolute guest paths; they must never be followed during extraction. The installer
extracts all regular files first across the selected packs, validates link parents/targets,
then creates links and switches its staged generation atomically. `baseVersion` is `null` for
base and an exact required base release for optional packs. An overlay may add files but may
not alter the base. Shared optional files must have identical bytes, modes and link targets.

The catalog uses `format`, `version` and `packs`. Each pack entry has `id`, `version`, `abi`,
`baseVersion`, `url`, `sha256`, `bytes`, `unpackedBytes`, `components`, `sources` and `licenses`.
`unpackedBytes` is the sum of regular-file sizes. Manifest modes are decimal JSON numbers.
Rootfs archives and component APKs are verified build inputs, never installer inputs.

Build gates cap manifest data at 8 MiB, archive entries and manifest paths at 64,000,
each regular file at 1 GiB, each packed archive and unpacked pack at 2 GiB and a selected ABI pack set
at 4 GiB. Paths have at most 64 components and 4096 UTF-8 bytes. ZIP header sizes
must equal manifest declarations; bounded reads verify every payload SHA-256 before
a catalog can be created. Encrypted entries, special ZIP types/modes, unsafe
symlinks and directories without owner read/execute permissions are rejected.
