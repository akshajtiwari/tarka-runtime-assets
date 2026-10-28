"""Create verified ZIP overlays without ZIP symlink entries."""
import hashlib
import json
import os
from pathlib import Path
import stat
import shutil
import zipfile

from paths import validate_paths

IGNORED = ('lib/apk/db', 'var/cache/apk', 'etc/apk/world')

def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def scan(root):
    entries = {}
    pending = [root]
    while pending:
        folder = pending.pop()
        for path in sorted(folder.iterdir()):
            name = path.relative_to(root).as_posix()
            if any(name == prefix or name.startswith(prefix + '/') for prefix in IGNORED):
                continue
            info = path.lstat()
            mode = stat.S_IMODE(info.st_mode) & 0o777
            if path.is_symlink():
                entries[name] = {'path': name, 'target': os.readlink(path), 'kind': 'link'}
            elif path.is_dir():
                entries[name] = {'path': name, 'mode': mode, 'kind': 'directory'}
                pending.append(path)
            elif path.is_file():
                entries[name] = {'path': name, 'mode': mode, 'size': info.st_size,
                                 'sha256': digest(path), 'kind': 'file'}
            else:
                raise ValueError(f'Unsupported rootfs entry: {name}')
    validate_paths(entries)
    return entries


def overlay(entries, base):
    changed = {name: item for name, item in entries.items() if base.get(name) != item}
    changed_base = [name for name in base if entries.get(name) != base[name]]
    if changed_base:
        raise ValueError('Optional pack alters base files: ' + ', '.join(changed_base[:8]))
    return changed


def write_pack(root, output, pack_id, abi, version, base=None, components=None):
    entries = scan(root)
    selected = overlay(entries, base) if base is not None else entries
    manifest = {'format': 1, 'id': pack_id, 'version': version, 'abi': abi,
                'baseVersion': version if base is not None else None,
                'directories': [], 'files': [], 'links': [], 'components': components or []}
    for name in sorted(selected):
        item = dict(selected[name])
        kind = item.pop('kind')
        key = {'file': 'files', 'directory': 'directories', 'link': 'links'}[kind]
        manifest[key].append(item)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr(zip_entry('manifest.json', 0o644),
                         json.dumps(manifest, sort_keys=True, separators=(',', ':')))
        for item in manifest['files']:
            with (root / item['path']).open('rb') as source:
                with archive.open(zip_entry('files/' + item['path'], item['mode']), 'w') as target:
                    shutil.copyfileobj(source, target, 1024 * 1024)
    return manifest, entries


def verify_overlap(manifests):
    seen = {}
    for manifest in manifests:
        for key in ('directories', 'files', 'links'):
            for item in manifest[key]:
                name = item['path']
                record = (key, item)
                if name in seen and seen[name] != record:
                    raise ValueError(f'Conflicting optional pack entry: {name}')
                seen[name] = record
    kinds = {'directories': 'directory', 'files': 'file', 'links': 'link'}
    validate_paths({name: dict(item, kind=kinds[key]) for name, (key, item) in seen.items()})


def zip_entry(name, mode):
    entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    entry.create_system = 3
    entry.external_attr = (stat.S_IFREG | mode) << 16
    entry.compress_type = zipfile.ZIP_DEFLATED
    return entry
