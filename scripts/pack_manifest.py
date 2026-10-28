"""Validate pack metadata and ZIP headers before reading payloads."""
import json
import re
import stat
import zipfile

from paths import validate_paths

MAX_FILE_BYTES = 1024 * 1024 * 1024
MAX_PACK_BYTES = 2 * MAX_FILE_BYTES
MAX_ARCHIVE_BYTES = 2 * MAX_FILE_BYTES
MAX_SET_BYTES = 4 * MAX_FILE_BYTES
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_ENTRIES = 64000


def validate_archive_file(path):
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError('Packed archive exceeds the allowed size: ' + str(path))


def regular_entry(entry):
    kind = stat.S_IFMT(entry.external_attr >> 16)
    mode = (entry.external_attr >> 16) & 0o7777
    if entry.is_dir() or entry.external_attr & 0x10 or kind not in (0, stat.S_IFREG) or mode & 0o7000:
        raise ValueError('ZIP entries must be regular files without special modes.')
    if entry.flag_bits & 1 or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
        raise ValueError('Encrypted or unsupported ZIP entry.')


def read_manifest(archive):
    entries = archive.infolist()
    if not entries or entries[0].filename != 'manifest.json' or entries[0].file_size > MAX_MANIFEST_BYTES:
        raise ValueError('Missing, misplaced or oversized manifest.')
    if len(entries) > MAX_ENTRIES:
        raise ValueError('ZIP has too many entries.')
    for entry in entries:
        regular_entry(entry)
    with archive.open(entries[0]) as stream:
        data = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(data) > MAX_MANIFEST_BYTES:
        raise ValueError('Oversized manifest.')
    manifest = json.loads(data)
    if manifest['format'] != 1:
        raise ValueError('Unsupported pack format.')
    expected = ['manifest.json'] + ['files/' + item['path'] for item in manifest['files']]
    if [entry.filename for entry in entries] != expected:
        raise ValueError('Archive payload differs from manifest.')
    mapping = {}
    total = 0
    for key, kind in (('directories', 'directory'), ('files', 'file'), ('links', 'link')):
        for item in manifest[key]:
            if item['path'] in mapping:
                raise ValueError('Duplicate manifest path.')
            mapping[item['path']] = dict(item, kind=kind)
            if kind != 'link':
                mode = item['mode']
                if type(mode) is not int or mode < 0 or mode > 0o777:
                    raise ValueError('Unsafe manifest mode.')
                if kind == 'directory' and mode & 0o500 != 0o500:
                    raise ValueError('Directory mode must retain owner read and execute.')
            if kind == 'file':
                size = item['size']
                if type(size) is not int or size < 0 or size > MAX_FILE_BYTES:
                    raise ValueError('File exceeds the allowed size.')
                if not re.fullmatch('[0-9a-f]{64}', item['sha256']):
                    raise ValueError('Invalid file SHA-256.')
                total += size
    if len(mapping) > MAX_ENTRIES or total > MAX_PACK_BYTES:
        raise ValueError('Pack exceeds entry or unpacked size limits.')
    validate_paths(mapping)
    for entry, item in zip(entries[1:], manifest['files']):
        if entry.file_size != item['size']:
            raise ValueError('ZIP file size differs from manifest: ' + item['path'])
    return manifest


def validate_identity(manifest, pack_id, abi, version):
    if manifest['id'] != pack_id or manifest['abi'] != abi:
        raise ValueError('Pack identity differs from its release filename.')
    if not isinstance(manifest['version'], str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,63}', manifest['version']):
        raise ValueError('Invalid pack version.')
    if manifest['version'] != version:
        raise ValueError('Pack versions differ.')
    expected = None if pack_id == 'base' else version
    if manifest['baseVersion'] != expected:
        raise ValueError('Pack baseVersion differs from the required base release.')


def unpacked_bytes(manifest):
    return sum(item['size'] for item in manifest['files'])
