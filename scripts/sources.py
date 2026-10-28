"""Collect exact aports recipes, patches and checksum-verified upstream sources."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

from pack_tree import digest, zip_entry


def recipe_files(component, destination, cache):
    commit = component['commit']
    if not commit or len(commit) != 40 or any(char not in '0123456789abcdef' for char in commit):
        raise ValueError('A component has no immutable source commit: ' + component['name'])
    archive = cache / (commit + '.tar.gz')
    if not archive.exists():
        temporary = archive.with_suffix('.part')
        urllib.request.urlretrieve(f'https://codeload.github.com/alpinelinux/aports/tar.gz/{commit}', temporary)
        temporary.rename(archive)
    prefix = f"aports-{commit}/{component['repository']}/{component['origin']}/"
    with tarfile.open(archive, 'r:gz') as stream:
        for item in stream:
            if not item.name.startswith(prefix):
                continue
            item.name = item.name[len(prefix):]
            if item.name:
                stream.extract(item, destination, filter='data')
    if not (destination / 'APKBUILD').is_file():
        raise ValueError('Exact aports recipe was not found: ' + prefix)


def collect(component, output, work, cache):
    source_id = component['origin'] + '-' + component['commit'][:12]
    destination = output / (source_id + '.zip')
    metadata = output / (source_id + '.json')
    if metadata.exists() and destination.exists():
        return json.loads(metadata.read_text())
    folder = work / source_id
    folder.mkdir(parents=True, exist_ok=True)
    recipe_files(component, folder, cache)
    environment = dict(os.environ, SRCDEST=str(folder / 'sources'),
                       DISTFILES_MIRROR='https://distfiles.alpinelinux.org/distfiles/v3.22')
    with (folder / 'fetch.log').open('w') as log:
        subprocess.run(['abuild', '-F', 'fetch', 'verify'], cwd=folder, env=environment,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=900)
    provenance = {'id': source_id, 'origin': component['origin'], 'commit': component['commit'],
                  'repository': component['repository'], 'license': component['license'],
                  'recipeUrl': f"https://github.com/alpinelinux/aports/tree/{component['commit']}/{component['repository']}/{component['origin']}",
                  'verification': 'abuild fetch verify; exact APKBUILD checksums'}
    (folder / 'PROVENANCE.json').write_text(json.dumps(provenance, indent=2) + '\n')
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(folder.rglob('*')):
            if file.is_file() and file.name != 'fetch.log':
                name = file.relative_to(folder).as_posix()
                with file.open('rb') as source, archive.open(zip_entry(name, 0o644), 'w') as target:
                    shutil.copyfileobj(source, target, 1024 * 1024)
    result = dict(provenance, file=destination.name, sha256=digest(destination), bytes=destination.stat().st_size)
    metadata.write_text(json.dumps(result, indent=2) + '\n')
    shutil.rmtree(folder)
    return result


def main():
    output = Path('.artifacts/release/sources').resolve()
    work = Path('.artifacts/source-work').resolve()
    cache = Path('.artifacts/source-recipes').resolve()
    for folder in (output, work, cache):
        folder.mkdir(parents=True, exist_ok=True)
    components = {}
    for filename in sys.argv[1:]:
        for manifest in json.loads(Path(filename).read_text()):
            for item in manifest['components']:
                components[(item['origin'], item['commit'])] = item
    failures = []
    records = []
    for item in components.values():
        try:
            print('Collecting sources: ' + item['origin'], flush=True)
            records.append(collect(item, output, work, cache))
        except Exception as error:
            failures.append({'origin': item['origin'], 'commit': item['commit'], 'error': str(error)})
            print('Source collection failed: ' + str(error), flush=True)
    (output / 'index.json').write_text(json.dumps({'sources': records, 'failures': failures}, indent=2) + '\n')
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
