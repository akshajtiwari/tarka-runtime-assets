"""Record exact Alpine package inputs, with their original signatures verified."""
import subprocess
import tarfile
import urllib.request
import urllib.error

from pack_tree import digest


def installed(database):
    result = []
    for record in database.read_text().split('\n\n'):
        fields = {}
        for line in record.splitlines():
            if line.startswith('F:'):
                break
            if len(line) > 2 and line[1] == ':':
                fields[line[0]] = line[2:]
        if 'P' in fields:
            result.append({'name': fields['P'], 'version': fields['V'],
                           'license': fields['L'], 'origin': fields['o'],
                           'commit': fields.get('c'), 'architecture': fields['A']})
    return sorted(result, key=lambda item: item['name'])


def archive_metadata(archive):
    with tarfile.open(archive, 'r:gz') as package:
        stream = package.extractfile('.PKGINFO')
        if stream is None:
            raise ValueError('APK has no package metadata: ' + str(archive))
        fields = {}
        for line in stream.read().decode().splitlines():
            if ' = ' in line:
                key, value = line.split(' = ', 1)
                fields[key] = value
    return {'name': fields['pkgname'], 'version': fields['pkgver'],
            'license': fields['license'], 'origin': fields['origin'],
            'commit': fields.get('commit'), 'architecture': fields['arch']}


def lock_components(root, arch, cache, extras=()):
    records = installed(root / 'lib/apk/db/installed')
    records.extend(archive_metadata(path) for path in extras)
    cache.mkdir(parents=True, exist_ok=True)
    for item in records:
        name = f"{item['name']}-{item['version']}.apk"
        archive = cache / name
        url = locate_archive(name, arch, archive)
        subprocess.run(['apk', '--keys-dir', str(root / 'etc/apk/keys'), 'verify', str(archive)], check=True)
        actual = archive_metadata(archive)
        if any(actual[key] != item[key] for key in actual if key != 'architecture'):
            raise ValueError('Package metadata differs from installed input: ' + name)
        if actual['architecture'] not in (arch, 'noarch'):
            raise ValueError('Package architecture differs: ' + name)
        item['architecture'] = actual['architecture']
        item.update({'apkUrl': url, 'apkSha256': digest(archive),
                     'apkBytes': archive.stat().st_size,
                     'repository': 'community' if '/community/' in url else 'main'})
    return sorted(records, key=lambda item: item['name'])


def locate_archive(name, arch, archive):
    for repository in ('main', 'community'):
        url = f'https://dl-cdn.alpinelinux.org/alpine/v3.22/{repository}/{arch}/{name}'
        try:
            if archive.is_file():
                with urllib.request.urlopen(urllib.request.Request(url, method='HEAD')):
                    return url
            temporary = archive.with_suffix('.part')
            urllib.request.urlretrieve(url, temporary)
            temporary.rename(archive)
            return url
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
    raise ValueError('Exact package is absent from Alpine repositories: ' + name)
