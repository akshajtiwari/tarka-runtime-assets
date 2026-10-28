import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from components import installed, lock_components, locate_archive
from pack_tree import write_pack, verify_overlap

VERSION = os.environ.get('PACK_VERSION', '2026.10.28.1')
PACKAGES = {'python': ['python3', 'py3-pip'],
            'java': ['openjdk17-jdk', 'maven'],
            'cpp': ['build-base', 'cmake', 'ninja', 'zlib-dev']}


def main(build, arch, abi):
    output = Path('.artifacts/release')
    base = build / 'base'
    prepare_base(base)
    # Pin every installed base package so optional tools cannot upgrade it implicitly.
    constraints = [f"{item['name']}={item['version']}" for item in installed(base / 'lib/apk/db/installed')]
    (base / 'etc/apk/world').write_text('\n'.join(constraints) + '\n')
    components = lock_components(base, arch, Path('.artifacts/apks') / arch)
    manifest, baseline = write_pack(base, output / f'base-{abi}.zip', 'base', abi, VERSION, components=components)
    manifests = [manifest]
    for pack_id, packages in PACKAGES.items():
        root = build / pack_id
        shutil.copytree(base, root, symlinks=True)
        subprocess.run(['apk', '--root', str(root), '--arch', arch, '--no-scripts',
                        '--cache-max-age', '999999', 'add', *packages], check=True)
        extras = []
        if pack_id == 'java':
            extras = prepare_java(root, arch)
        components = lock_components(root, arch, Path('.artifacts/apks') / arch, extras)
        manifest, _ = write_pack(root, output / f'{pack_id}-{abi}.zip', pack_id, abi, VERSION,
                                 base=baseline, components=components)
        manifests.append(manifest)
        shutil.rmtree(root)
    verify_overlap(manifests[1:])
    (output / f'manifests-{abi}.json').write_text(json.dumps(manifests, indent=2) + '\n')


def prepare_base(root):
    # Binutils supplies GNU strings in the C/C++ overlay; keep base immutable.
    strings = root / 'usr/bin/strings'
    if strings.is_symlink() and 'busybox' in str(strings.readlink()):
        strings.unlink()
    elif strings.exists():
        raise ValueError('Unexpected owner of the base strings command.')
    passwd = root / 'etc/passwd'
    lines = passwd.read_text().splitlines()
    for index, line in enumerate(lines):
        fields = line.split(':')
        if fields[0] != 'root':
            continue
        # Java derives user.home from passwd rather than the HOME environment.
        fields[5] = '/home/tarka'
        lines[index] = ':'.join(fields)
        passwd.write_text('\n'.join(lines) + '\n')
        return
    raise ValueError('The base root account is missing.')


def prepare_java(root, arch):
    cache = Path('.artifacts/apks') / arch
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / 'gradle-8.14.1-r0.apk'
    locate_archive(archive.name, arch, archive)
    subprocess.run(['apk', '--keys-dir', str(root / 'etc/apk/keys'), 'verify', str(archive)], check=True)
    subprocess.run(['tar', '-xzf', str(archive), '-C', str(root), 'usr'], check=True)
    destination = root / 'etc/ssl/certs/java/cacerts'
    destination.parent.mkdir(parents=True, exist_ok=True)
    bundle = root / 'etc/ssl/certs/ca-certificates.crt'
    if bundle.read_bytes() != Path('/etc/ssl/certs/ca-certificates.crt').read_bytes():
        raise ValueError('Builder and target CA bundles differ; refusing a mismatched Java truststore.')
    subprocess.run(['trust', 'extract', '--overwrite', '--format=java-cacerts', '--filter=ca-anchors',
                    '--purpose', 'server-auth', str(destination)], check=True)
    jvm = root / 'usr/lib/jvm/default-jvm'
    if jvm.is_symlink():
        jvm.unlink()
    jvm.symlink_to('java-17-openjdk')
    if any(path.name.startswith('java-21') for path in jvm.parent.iterdir()):
        raise ValueError('Java21 was unexpectedly included.')
    return [archive]


if __name__ == '__main__':
    main(Path(sys.argv[1]), sys.argv[2], sys.argv[3])
