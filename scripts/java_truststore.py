"""Normalize generated JKS creation dates without changing trusted certificates."""
import hashlib
import struct


def integrity_digest(payload):
    # This is the standard public Java cacerts password and JKS integrity format.
    return hashlib.sha1('changeit'.encode('utf-16be') + b'Mighty Aphrodite' + payload).digest()


def read_uint(payload, offset):
    if offset + 4 > len(payload):
        raise ValueError('Truncated Java truststore integer.')
    return struct.unpack_from('>I', payload, offset)[0]


def skip_utf(payload, offset):
    if offset + 2 > len(payload):
        raise ValueError('Truncated Java truststore string.')
    size = struct.unpack_from('>H', payload, offset)[0]
    end = offset + 2 + size
    if end > len(payload):
        raise ValueError('Truncated Java truststore string.')
    return end


def normalize_jks(data):
    if len(data) < 32 or len(data) > 8 * 1024 * 1024:
        raise ValueError('Java truststore size is outside supported bounds.')
    payload = bytearray(data[:-20])
    if integrity_digest(payload) != data[-20:]:
        raise ValueError('Java truststore integrity digest differs.')
    if read_uint(payload, 0) != 0xFEEDFEED or read_uint(payload, 4) != 2:
        raise ValueError('Expected a version 2 JKS Java truststore.')
    count = read_uint(payload, 8)
    if count > 4096:
        raise ValueError('Java truststore contains too many entries.')
    offset = 12
    for unused in range(count):
        if read_uint(payload, offset) != 2:
            raise ValueError('Only trusted certificate entries belong in Java cacerts.')
        offset = skip_utf(payload, offset + 4)
        if offset + 8 > len(payload):
            raise ValueError('Truncated Java truststore creation date.')
        # p11-kit stamps the current time; a fixed date makes both ABI packs reproducible.
        payload[offset:offset + 8] = bytes(8)
        offset = skip_utf(payload, offset + 8)
        size = read_uint(payload, offset)
        offset += 4 + size
        if offset > len(payload):
            raise ValueError('Truncated Java truststore certificate.')
    if offset != len(payload):
        raise ValueError('Unexpected trailing Java truststore data.')
    return bytes(payload) + integrity_digest(payload)
