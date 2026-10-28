"""Verify release payloads and stage them for isolated Linux smoke tests."""
from pathlib import Path
import sys
import zipfile

from pack_tree import verify_overlap
from pack_manifest import MAX_SET_BYTES, read_manifest, unpacked_bytes, validate_archive_file
from pack_payload import copy_verified


def stage(archives, destination):
    if destination.exists():
        raise ValueError('Verification destination already exists: ' + str(destination))
    manifests = []
    for filename in archives:
        validate_archive_file(filename)
        with zipfile.ZipFile(filename) as archive:
            manifests.append(read_manifest(archive))
    verify_overlap(manifests)
    if sum(unpacked_bytes(manifest) for manifest in manifests) > MAX_SET_BYTES:
        raise ValueError('Combined packs exceed unpacked limits.')
    remaining = MAX_SET_BYTES
    destination.mkdir(parents=True)
    for filename, manifest in zip(archives, manifests):
        with zipfile.ZipFile(filename) as archive:
            for item in manifest['directories']:
                target = destination / item['path']
                target.mkdir(parents=True, exist_ok=True)
                target.chmod(item['mode'])
            for item in manifest['files']:
                target = destination / item['path']
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open('files/' + item['path']) as source, target.open('wb') as output:
                    remaining -= copy_verified(source, output, item, remaining)
                target.chmod(item['mode'])
    # No host operation follows these symlinks; absolute targets belong to the guest.
    for manifest in manifests:
        for item in manifest['links']:
            target = destination / item['path']
            if not target.is_symlink():
                target.symlink_to(item['target'])
    print('Verified and staged ' + str(destination))


if __name__ == '__main__':
    abi = sys.argv[1]
    stage([Path(f'.artifacts/release/{name}-{abi}.zip') for name in ('base', 'python', 'java', 'cpp')],
          Path('.artifacts/verified') / abi)
