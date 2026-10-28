"""Add sources for binary-only Java distributions and bundled copyleft libraries."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import urllib.request
import zipfile

from pack_tree import digest, zip_entry
from java_source_trees import collect


def fetch(url, destination, algorithm):
    destination.parent.mkdir(parents=True, exist_ok=True)
    checksum_url = url + '.' + algorithm
    with urllib.request.urlopen(checksum_url) as response:
        expected = response.read().decode().split()[0].lower()
    if not destination.exists():
        temporary = destination.with_suffix('.part')
        urllib.request.urlretrieve(url, temporary)
        temporary.rename(destination)
    result = hashlib.new(algorithm)
    with destination.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    if result.hexdigest() != expected:
        raise ValueError('Upstream source checksum differs: ' + url)
    return {'url': url, 'upstreamChecksumUrl': checksum_url, 'upstreamAlgorithm': algorithm,
            'upstreamChecksum': expected, 'sha256': digest(destination), 'bytes': destination.stat().st_size}


def library_sources(item, root, folder):
    name = f"{item['artifact']}-{item['version']}"
    matches = list((root / 'usr/share/java').rglob(name + '.jar'))
    if not matches:
        raise ValueError('Declared library is absent from Java pack: ' + name)
    url = 'https://repo.maven.apache.org/maven2/' + item['group'].replace('.', '/')
    url += f"/{item['artifact']}/{item['version']}/{name}"
    with urllib.request.urlopen(url + '.jar.sha1') as response:
        expected = response.read().decode().strip().split()[0]
    if any(hashlib.sha1(path.read_bytes()).hexdigest() != expected for path in matches):
        raise ValueError('Shipped Java binary differs from Maven Central: ' + name)
    record = dict(item, shippedBinarySha256=digest(matches[0]), sources=[])
    for suffix in ('-sources.jar', '.pom'):
        destination = folder / 'libraries' / (name + suffix)
        record['sources'].append(fetch(url + suffix, destination, 'sha1'))
    return record


def main():
    folder = Path('.artifacts/java-sources')
    root = Path('.artifacts/verified/x86_64')
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    distributions = (
        ('https://services.gradle.org/distributions/gradle-8.14.1-src.zip', 'sha256'),
        ('https://archive.apache.org/dist/maven/maven-3/3.9.9/source/apache-maven-3.9.9-src.tar.gz', 'sha512'),
    )
    for url, algorithm in distributions:
        print('Collecting Java source distribution: ' + url.rsplit('/', 1)[1], flush=True)
        records.append(fetch(url, folder / 'distributions' / url.rsplit('/', 1)[1], algorithm))
    libraries = json.loads(Path('config/java-components.json').read_text())
    for item in libraries:
        print('Collecting bundled Java library: ' + item['artifact'], flush=True)
        records.append(library_sources(item, root, folder))
    records.extend(collect(folder))
    for jar in (root / 'usr/share/java').rglob('*.jar'):
        with zipfile.ZipFile(jar) as archive:
            for name in archive.namelist():
                if not name.endswith('/') and any(word in name.upper() for word in ('LICENSE', 'NOTICE', 'COPYING')):
                    path = PurePosixPath(name)
                    if path.is_absolute() or '..' in path.parts or '\\' in name:
                        raise ValueError('Unsafe notice path: ' + name)
                    destination = folder / 'notices' / jar.name / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.read(name))
    gradle_notices = root / 'usr/share/licenses/gradle'
    shutil.copytree(gradle_notices, folder / 'notices/gradle', dirs_exist_ok=True)
    (folder / 'PROVENANCE.json').write_text(json.dumps(records, indent=2) + '\n')
    output = Path('.artifacts/release/java-corresponding-sources.zip')
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(folder.rglob('*')):
            if file.is_file():
                with file.open('rb') as source, archive.open(zip_entry(file.relative_to(folder).as_posix(), 0o644), 'w') as target:
                    shutil.copyfileobj(source, target, 1024 * 1024)
    metadata = {'file': output.name, 'sha256': digest(output), 'bytes': output.stat().st_size,
                'libraries': libraries, 'verification': 'Exact binary SHA-1 matched Maven Central; source upstream checksums verified.'}
    Path('.artifacts/release/java-sources.json').write_text(json.dumps(metadata, indent=2) + '\n')


if __name__ == '__main__':
    main()
