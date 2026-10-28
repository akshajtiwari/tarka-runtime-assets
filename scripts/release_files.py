"""Write checksums and an explicit flat GitHub Release upload list."""
from pathlib import Path
import shutil
import sys

from pack_tree import digest


def main(stage=False):
    root = Path('.artifacts/release')
    shutil.copyfile(root / 'sources/index.json', root / 'source-index.json')
    names = ['catalog.json', 'licenses.zip', 'licenses.json', 'source-index.json',
             'java-corresponding-sources.zip', 'java-sources.json',
             'native-loader-corresponding-sources.zip', 'native-sources.json',
             'manifests-arm64-v8a.json', 'manifests-x86_64.json']
    if (root / 'build-source.json').is_file():
        names.append('build-source.json')
    files = [root / name for name in names]
    files.extend(root / f'{pack}-{abi}.zip' for abi in ('arm64-v8a', 'x86_64')
                 for pack in ('base', 'python', 'java', 'cpp'))
    files.extend(sorted((root / 'sources').glob('*.zip')))
    if len({file.name for file in files}) != len(files):
        raise ValueError('Release assets have duplicate basenames.')
    checksum = root / 'SHA256SUMS'
    checksum.write_text(''.join(f'{digest(file)}  {file.name}\n' for file in files))
    files.append(checksum)
    (root / 'UPLOADS.txt').write_text(''.join(str(file) + '\n' for file in files))
    if stage:
        destination = Path('.artifacts/release-upload')
        destination.mkdir()
        for file in files:
            shutil.copyfile(file, destination / file.name)
    print(f'Prepared {len(files)} flat release assets; no files uploaded.')


if __name__ == '__main__':
    main(stage='--stage' in sys.argv[1:])
