"""Check extracted native files match the requested ABI; this does not execute them."""
from pathlib import Path
import struct
import sys


def check(root, abi):
    expected = {'x86_64': 62, 'arm64-v8a': 183}[abi]
    count = 0
    for path in root.rglob('*'):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open('rb') as stream:
            header = stream.read(20)
        if header[:4] != b'\x7fELF':
            continue
        if len(header) != 20 or header[4:6] != bytes((2, 1)):
            raise ValueError('Expected a 64-bit little-endian ELF: ' + str(path))
        machine = struct.unpack_from('<H', header, 18)[0]
        if machine != expected:
            raise ValueError('ELF architecture differs: ' + str(path))
        count += 1
    print(f'{abi}: checked {count} native ELF files; execution remains a separate test.')


if __name__ == '__main__':
    check(Path('.artifacts/verified') / sys.argv[1], sys.argv[1])
