"""Check a flat build artifact without executing or extracting its toolchains."""
import json
import os
from pathlib import Path
import re
import sys

from candidate_build import validate_inputs, validate_provenance
from pack_manifest import validate_identity
from pack_tree import digest

ABIS = ('arm64-v8a', 'x86_64')
PACKS = ('base', 'python', 'java', 'cpp')
FIXED = {'catalog.json', 'licenses.zip', 'licenses.json', 'source-index.json',
         'java-corresponding-sources.zip', 'java-sources.json', 'build-source.json',
         'native-loader-corresponding-sources.zip', 'native-sources.json',
         'manifests-arm64-v8a.json', 'manifests-x86_64.json', 'SHA256SUMS'}


def read_json(folder, name):
    path = folder / name
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError('Candidate JSON is too large: ' + name)
    return json.loads(path.read_text())


def checksums(folder):
    path = folder / 'SHA256SUMS'
    if path.stat().st_size > 65536:
        raise ValueError('Candidate checksum list is too large.')
    records = {}
    for line in path.read_text().splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9._+-]{0,159})', line)
        if not match or match[2] in records or '..' in match[2]:
            raise ValueError('Invalid or duplicate candidate checksum entry.')
        records[match[2]] = match[1]
    return records


def verify_record(record, name, folder, hashes):
    if record.get('file', name) != name or record.get('sha256') != hashes.get(name):
        raise ValueError('Candidate integrity record differs: ' + name)
    if type(record.get('bytes')) is not int or record['bytes'] != (folder / name).stat().st_size:
        raise ValueError('Candidate size record differs: ' + name)


def verify_candidate(folder, repository, version, run_id, commit):
    validate_inputs(repository, version, run_id)
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Expected build commit is invalid.')
    files = list(folder.iterdir())
    if len(files) > 512 or any(file.is_symlink() or not file.is_file() for file in files):
        raise ValueError('Candidate must contain bounded, flat regular files only.')
    if any(file.stat().st_size > 2 * 1024 ** 3 for file in files):
        raise ValueError('Candidate file exceeds its size limit.')
    if sum(file.stat().st_size for file in files) > 8 * 1024 ** 3:
        raise ValueError('Candidate artifact exceeds its total size limit.')
    hashes = checksums(folder)
    catalog = read_json(folder, 'catalog.json')
    sources = read_json(folder, 'source-index.json')
    if catalog.get('format') != 1 or catalog.get('version') != version or sources.get('failures') != []:
        raise ValueError('Candidate catalog version or source completeness differs.')
    expected = set(FIXED)
    expected.update(f'{pack}-{abi}.zip' for abi in ABIS for pack in PACKS)
    source_keys = set()
    source_records = {}
    for source in sources['sources']:
        origin, source_commit = source['origin'], source['commit']
        if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9._+-]{0,127}', origin):
            raise ValueError('Candidate source origin is invalid.')
        if not re.fullmatch('[0-9a-f]{40}', source_commit):
            raise ValueError('Candidate source revision is invalid.')
        name = origin + '-' + source_commit[:12] + '.zip'
        if source.get('file') != name or (origin, source_commit) in source_keys:
            raise ValueError('Candidate source archive identity differs.')
        expected.add(name)
        source_keys.add((origin, source_commit))
        source_records[(origin, source_commit)] = source
        verify_record(source, name, folder, hashes)
    if {file.name for file in files} != expected or set(hashes) != expected - {'SHA256SUMS'}:
        raise ValueError('Candidate files differ from the complete flat allowlist.')
    for name, expected_hash in hashes.items():
        if digest(folder / name) != expected_hash:
            raise ValueError('Candidate checksum differs: ' + name)
    validate_provenance(read_json(folder, 'build-source.json'), repository, version, run_id, commit)
    base_url = f'https://github.com/{repository}/releases/download/{version}/'
    packs = catalog.get('packs', [])
    if len(packs) != 8 or {(item['id'], item['abi']) for item in packs} != {(p, a) for p in PACKS for a in ABIS}:
        raise ValueError('Candidate must contain all eight runtime packs exactly once.')
    metadata = {'licenses.zip': read_json(folder, 'licenses.json'),
                'java-corresponding-sources.zip': read_json(folder, 'java-sources.json'),
                'native-loader-corresponding-sources.zip': read_json(folder, 'native-sources.json')}
    for name, record in metadata.items():
        verify_record(record, name, folder, hashes)
    required_sources = set()
    for pack in packs:
        validate_identity(pack, pack['id'], pack['abi'], version)
        name = pack['id'] + '-' + pack['abi'] + '.zip'
        if pack.get('url') != base_url + name:
            raise ValueError('Candidate pack URL differs from the selected release.')
        verify_record(pack, name, folder, hashes)
        required = {(item['origin'], item['commit']) for item in pack['components']}
        required_sources.update(required)
        references = [source_records[key] for key in sorted(required)]
        if pack['id'] == 'java':
            references.append(metadata['java-corresponding-sources.zip'])
        if pack.get('sources') != [dict(item, url=base_url + item['file']) for item in references]:
            raise ValueError('Candidate catalog source references differ.')
        if pack.get('licenses') != dict(metadata['licenses.zip'], url=base_url + 'licenses.zip'):
            raise ValueError('Candidate catalog license reference differs.')
    if required_sources != source_keys:
        raise ValueError('Candidate corresponding sources differ from pack components.')
    native = metadata['native-loader-corresponding-sources.zip']
    if catalog.get('nativeSources') != dict(native, url=base_url + native['file']):
        raise ValueError('Candidate native source reference differs.')
    return sorted(folder / name for name in expected)


if __name__ == '__main__':
    verify_candidate(Path(sys.argv[1]), os.environ['ASSET_REPOSITORY'], os.environ['BUILD_VERSION'],
                     os.environ['BUILD_RUN_ID'], os.environ['BUILD_COMMIT'])
    print('Candidate allowlist, checksums, catalog and build provenance verified.')
