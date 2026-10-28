"""Bundle declared license texts; original notices remain in corresponding sources."""
import json
from pathlib import Path
import re
import sys
import urllib.request
import zipfile

from pack_tree import digest, zip_entry

SPDX_VERSION = 'v3.27.0'


def identifiers(expression):
    return sorted(set(re.findall(r'[A-Za-z0-9.+-]+', expression.replace('Public Domain', 'Public-Domain').replace('GPL-2.0-with-classpath-exception', 'GPL-2.0-only WITH Classpath-exception-2.0'))) - {'AND', 'OR', 'WITH'})


def main():
    output = Path('.artifacts/release')
    components = {}
    for filename in sys.argv[1:]:
        for manifest in json.loads(Path(filename).read_text()):
            for item in manifest['components']:
                components[(item['name'], item['version'])] = item
    java = json.loads((output / 'java-sources.json').read_text())
    expressions = sorted({item['license'] for item in components.values()} |
                         {item['license'] for item in java['libraries']})
    texts = {}
    provenance = {}
    for license_id in sorted({name for expression in expressions for name in identifiers(expression)}):
        if license_id == 'Public-Domain':
            texts[license_id] = ('Alpine declares Public-Domain for portions of these components.\n'
                                 'This is a metadata label, not a uniform license. Consult original\n'
                                 'copyright and dedication notices in the matching source archives.\n')
            provenance[license_id] = {'type': 'component-source-notices'}
            continue
        print('Fetching license: ' + license_id, flush=True)
        url = f'https://raw.githubusercontent.com/spdx/license-list-data/{SPDX_VERSION}/text/{license_id}.txt'
        with urllib.request.urlopen(url) as response:
            texts[license_id] = response.read().decode()
        provenance[license_id] = {'type': 'SPDX', 'url': url}
    destination = output / 'licenses.zip'
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for license_id, content in texts.items():
            archive.writestr(zip_entry(license_id + '.txt', 0o644), content)
        notices = Path('.artifacts/java-sources/notices')
        for file in sorted(notices.rglob('*')):
            if file.is_file():
                archive.writestr(zip_entry('java-notices/' + file.relative_to(notices).as_posix(), 0o644), file.read_bytes())
        manifest = {'expressions': expressions, 'texts': provenance, 'components': list(components.values()),
                    'notice': 'Original copyright notices and component-specific terms are in corresponding source archives.'}
        archive.writestr(zip_entry('NOTICE.json', 0o644), json.dumps(manifest, indent=2))
    (output / 'licenses.json').write_text(json.dumps({'file': destination.name,
        'sha256': digest(destination), 'bytes': destination.stat().st_size,
        'expressions': expressions}, indent=2) + '\n')


if __name__ == '__main__':
    main()
