"""Create a release catalog only when every pack has its sources and licenses."""
import json
from pathlib import Path
import sys
import zipfile

from pack_tree import digest, verify_overlap
from pack_manifest import MAX_SET_BYTES, read_manifest, unpacked_bytes, validate_archive_file, validate_identity
from pack_payload import verify_payload

ABIS = ('arm64-v8a', 'x86_64')
PACKS = ('base', 'python', 'java', 'cpp')


def source_references(components, sources, base_url):
    required = {(item['origin'], item['commit']) for item in components}
    indexed = {(item['origin'], item['commit']): item for item in sources}
    result = []
    for key in sorted(required):
        if key not in indexed:
            raise ValueError('Missing corresponding source archive: ' + str(key))
        record = indexed[key]
        result.append(dict(record, url=base_url + '/' + record['file']))
    return result


def verify_file(record, directory):
    path = directory / record['file']
    if not path.is_file() or path.stat().st_size != record['bytes'] or digest(path) != record['sha256']:
        raise ValueError('Release asset differs from its integrity record: ' + str(path))


def main(base_url, output=Path('.artifacts/release')):
    if not base_url.startswith('https://') or base_url.endswith('/'):
        raise ValueError('Pass an HTTPS release asset URL without a trailing slash.')
    source_index = json.loads((output / 'sources/index.json').read_text())
    if source_index['failures']:
        raise ValueError('Source collection still has failures.')
    licenses = json.loads((output / 'licenses.json').read_text())
    java = json.loads((output / 'java-sources.json').read_text())
    native = json.loads((output / 'native-sources.json').read_text())
    verify_file(native, output)
    for record in source_index['sources']:
        verify_file(record, output / 'sources')
    verify_file(licenses, output)
    verify_file(java, output)
    records = []
    versions = set()
    for abi in ABIS:
        manifests = []
        for pack_id in PACKS:
            path = output / f'{pack_id}-{abi}.zip'
            validate_archive_file(path)
            with zipfile.ZipFile(path) as archive:
                manifest = read_manifest(archive)
                version = manifests[0]['version'] if manifests else manifest['version']
                validate_identity(manifest, pack_id, abi, version)
                verify_payload(archive, manifest)
            manifests.append(manifest)
            versions.add(manifest['version'])
            sources = source_references(manifest['components'], source_index['sources'], base_url)
            if pack_id == 'java':
                sources.append(dict(java, url=base_url + '/' + java['file']))
            record = {key: manifest[key] for key in ('id', 'version', 'abi', 'baseVersion', 'components')}
            record.update({'url': base_url + '/' + path.name, 'sha256': digest(path),
                           'bytes': path.stat().st_size,
                           'unpackedBytes': sum(item['size'] for item in manifest['files']),
                           'sources': sources, 'licenses': dict(licenses, url=base_url + '/licenses.zip')})
            records.append(record)
        verify_overlap(manifests)
        if sum(unpacked_bytes(manifest) for manifest in manifests) > MAX_SET_BYTES:
            raise ValueError('Combined packs exceed unpacked limits.')
    if len(versions) != 1:
        raise ValueError('Pack versions differ.')
    (output / 'catalog.json').write_text(json.dumps({'format': 1, 'version': versions.pop(),
                                                   'packs': records,
                                                   'nativeSources': dict(native, url=base_url + '/' + native['file'])}, indent=2) + '\n')


if __name__ == '__main__':
    main(sys.argv[1])
