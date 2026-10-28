"""Bound and hash each payload while reading, with optional extraction."""
import hashlib

from pack_manifest import MAX_FILE_BYTES, MAX_PACK_BYTES


def copy_verified(source, output, item, remaining):
    limit = min(item['size'], MAX_FILE_BYTES, remaining)
    written = 0
    result = hashlib.sha256()
    while True:
        block = source.read(min(1024 * 1024, limit - written + 1))
        if not block:
            break
        if len(block) > limit - written:
            raise ValueError('Payload exceeds declared size or unpacked limit: ' + item['path'])
        written += len(block)
        result.update(block)
        if output is not None:
            output.write(block)
    if written != item['size'] or result.hexdigest() != item['sha256']:
        raise ValueError('Payload size or hash differs: ' + item['path'])
    return written


def verify_payload(archive, manifest):
    remaining = MAX_PACK_BYTES
    for item in manifest['files']:
        with archive.open('files/' + item['path']) as source:
            remaining -= copy_verified(source, None, item, remaining)
