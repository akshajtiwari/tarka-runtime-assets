import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from candidate_files import ABIS, FIXED, PACKS
from candidate_build_fixtures import COMMIT, REPOSITORY, RUN_ID, VERSION


def write_json(folder, name, record):
    (folder / name).write_text(json.dumps(record))


def file_record(folder, name):
    data = (folder / name).read_bytes()
    return {'file': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def write_checksums(folder):
    names = sorted(path.name for path in folder.iterdir() if path.name != 'SHA256SUMS')
    (folder / 'SHA256SUMS').write_text(''.join(file_record(folder, name)['sha256'] + '  ' + name + '\n'
                                             for name in names))


def make_candidate(folder):
    for name in FIXED - {'SHA256SUMS'}:
        (folder / name).write_bytes(b'public-asset')
    for abi in ABIS:
        for pack in PACKS:
            (folder / f'{pack}-{abi}.zip').write_bytes(('runtime-' + pack + abi).encode())
    source_name = 'compiler-' + 'b' * 12 + '.zip'
    (folder / source_name).write_bytes(b'corresponding source')
    source = dict(file_record(folder, source_name), origin='compiler', commit='b' * 40)
    write_json(folder, 'source-index.json', {'sources': [source], 'failures': []})
    for name, archive in [('licenses.json', 'licenses.zip'),
                          ('java-sources.json', 'java-corresponding-sources.zip'),
                          ('native-sources.json', 'native-loader-corresponding-sources.zip')]:
        write_json(folder, name, file_record(folder, archive))
    license_record = file_record(folder, 'licenses.zip')
    base_url = f'https://github.com/{REPOSITORY}/releases/download/{VERSION}/'
    packs = []
    for abi in ABIS:
        for pack in PACKS:
            name = pack + '-' + abi + '.zip'
            sources = [dict(source, url=base_url + source_name)]
            if pack == 'java':
                record = file_record(folder, 'java-corresponding-sources.zip')
                sources.append(dict(record, url=base_url + record['file']))
            record = dict(file_record(folder, name), id=pack, abi=abi, version=VERSION,
                          baseVersion=None if pack == 'base' else VERSION, url=base_url + name,
                          components=[{'origin': 'compiler', 'commit': 'b' * 40}], sources=sources,
                          licenses=dict(license_record, url=base_url + 'licenses.zip'))
            packs.append(record)
    native = file_record(folder, 'native-loader-corresponding-sources.zip')
    write_json(folder, 'catalog.json', {'format': 1, 'version': VERSION, 'packs': packs,
                                      'nativeSources': dict(native, url=base_url + native['file'])})
    write_json(folder, 'build-source.json', {'repository': REPOSITORY, 'version': VERSION, 'commit': COMMIT,
               'buildUrl': f'https://github.com/{REPOSITORY}/actions/runs/{RUN_ID}',
               'sourceUrl': f'https://github.com/{REPOSITORY}/tree/{COMMIT}'})
    write_checksums(folder)
