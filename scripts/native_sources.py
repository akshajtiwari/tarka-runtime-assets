"""Bundle only standalone native component sources, patches and build instructions."""
import json
from pathlib import Path
import shutil
import urllib.request
import zipfile

from pack_tree import digest, zip_entry


def main():
    inputs = json.loads(Path('native/source-lock.json').read_text())
    downloads = Path('.artifacts/native-loader/downloads')
    downloads.mkdir(parents=True, exist_ok=True)
    for item in inputs:
        destination = downloads / item['file']
        if not destination.exists():
            temporary = destination.with_suffix('.part')
            urllib.request.urlretrieve(item['url'], temporary)
            temporary.rename(destination)
        if digest(destination) != item['sha256']:
            raise ValueError('Native source archive checksum differs: ' + item['name'])
    for license_id in ('GPL-3.0-only', 'LGPL-3.0-only'):
        destination = Path('native/licenses') / (license_id + '.txt')
        url = f'https://raw.githubusercontent.com/spdx/license-list-data/v3.27.0/text/{license_id}.txt'
        if not destination.exists():
            urllib.request.urlretrieve(url, destination)
    output = Path('.artifacts/release/native-loader-corresponding-sources.zip')
    files = [(file, file.as_posix()) for file in Path('native').rglob('*') if file.is_file()]
    files.extend((downloads / item['file'], 'sources/' + item['file']) for item in inputs)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for file, name in sorted(files, key=lambda entry: entry[1]):
            mode = 0o755 if file.suffix == '.sh' else 0o644
            with file.open('rb') as source, archive.open(zip_entry(name, mode), 'w') as target:
                shutil.copyfileobj(source, target, 1024 * 1024)
    metadata = {'file': output.name, 'sha256': digest(output), 'bytes': output.stat().st_size,
                'components': inputs, 'api': 24, 'elfPageBytes': 16384}
    Path('.artifacts/release/native-sources.json').write_text(json.dumps(metadata, indent=2) + '\n')


if __name__ == '__main__':
    main()
