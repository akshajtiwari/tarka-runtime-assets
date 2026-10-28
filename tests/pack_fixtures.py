import hashlib
import json
import zipfile

from pack_tree import zip_entry


def manifest(pack_id='base', abi='arm64-v8a', payload=b'tool'):
    return {'format': 1, 'id': pack_id, 'abi': abi, 'version': 'test',
            'baseVersion': None if pack_id == 'base' else 'test', 'components': [],
            'directories': [], 'links': [],
            'files': [{'path': 'tool', 'mode': 0o755, 'size': len(payload),
                       'sha256': hashlib.sha256(payload).hexdigest()}]}


def write_archive(destination, record, payload=b'tool', extra=False):
    with zipfile.ZipFile(destination, 'w') as archive:
        archive.writestr(zip_entry('manifest.json', 0o644), json.dumps(record))
        archive.writestr(zip_entry('files/tool', 0o755), payload)
        if extra:
            archive.writestr(zip_entry('../unlisted', 0o644), 'malicious')
