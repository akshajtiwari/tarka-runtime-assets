"""Preserve original source trees and their build scripts for bundled Java libraries."""
import json
from pathlib import Path
import urllib.request

from pack_tree import digest


def download(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        temporary = destination.with_suffix('.part')
        urllib.request.urlretrieve(url, temporary)
        temporary.rename(destination)
    return {'url': url, 'sha256': digest(destination), 'bytes': destination.stat().st_size}


def collect(folder):
    records = []
    for item in json.loads(Path('config/java-source-commits.json').read_text()):
        url = f"https://codeload.github.com/{item['repository']}/tar.gz/{item['commit']}"
        archive = folder / 'source-trees' / (item['project'] + '-' + item['commit'][:12] + '.tar.gz')
        records.append(dict(item, **download(url, archive)))
    base = 'https://archive.debian.org/debian/pool/main/j/jcifs/'
    descriptor = folder / 'source-trees/jcifs_1.3.17-1.dsc'
    download(base + descriptor.name, descriptor)
    archive = folder / 'source-trees/jcifs_1.3.17.orig.tar.gz'
    record = download(base + archive.name, archive)
    expected = declared_checksum(descriptor.read_text(), archive.name)
    if expected is None or digest(archive) != expected:
        raise ValueError('Original JCIFS archive differs from the Debian source descriptor.')
    records.append(dict(record, descriptor=base + descriptor.name,
                        verification='SHA-256 matched the original source entry in the Debian descriptor.'))
    return records


def declared_checksum(text, name):
    expected = None
    in_sha256 = False
    for line in text.splitlines():
        if line.rstrip() == 'Checksums-Sha256:':
            in_sha256 = True
            continue
        if in_sha256 and not line.startswith(' '):
            break
        if in_sha256 and line.strip().endswith(' ' + name):
            expected = line.split()[0]
    return expected
