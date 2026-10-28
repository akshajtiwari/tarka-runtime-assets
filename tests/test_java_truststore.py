import hashlib
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from java_truststore import normalize_jks


def signed(payload):
    footer = hashlib.sha1('changeit'.encode('utf-16be') + b'Mighty Aphrodite' + payload).digest()
    return bytes(payload) + footer


def utf(value):
    return struct.pack('>H', len(value)) + value


def fixture(timestamp):
    header = struct.pack('>III', 0xFEEDFEED, 2, 2)
    entries = []
    for alias, certificate in [(b'root-a', b'first certificate'), (b'root-b', b'second certificate')]:
        entries.append(struct.pack('>I', 2) + utf(alias) + struct.pack('>q', timestamp)
                       + utf(b'X.509') + struct.pack('>I', len(certificate)) + certificate)
    return signed(header + b''.join(entries))


class JavaTruststoreTests(unittest.TestCase):
    def test_different_creation_times_normalize_to_same_valid_store(self):
        first = normalize_jks(fixture(123456789))
        second = normalize_jks(fixture(987654321))
        self.assertEqual(first, second)
        self.assertEqual(first, fixture(0))
        self.assertEqual(normalize_jks(first), first)

    def test_corrupt_footer_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'integrity digest'):
            normalize_jks(fixture(12)[:-1] + b'!')

    def test_private_key_entries_are_rejected(self):
        payload = bytearray(fixture(12)[:-20])
        struct.pack_into('>I', payload, 12, 1)
        with self.assertRaisesRegex(ValueError, 'Only trusted certificate'):
            normalize_jks(signed(payload))

    def test_malformed_headers_counts_and_trailing_data_are_rejected(self):
        for offset, value in [(0, 0), (4, 1), (8, 4097)]:
            payload = bytearray(fixture(12)[:-20])
            struct.pack_into('>I', payload, offset, value)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                normalize_jks(signed(payload))
        with self.assertRaisesRegex(ValueError, 'trailing'):
            normalize_jks(signed(fixture(12)[:-20] + b'!'))

    def test_truncated_fields_are_rejected_even_with_valid_footer(self):
        payload = fixture(12)[:-20]
        for end in range(len(payload)):
            with self.subTest(end=end), self.assertRaises(ValueError):
                normalize_jks(signed(payload[:end]))


if __name__ == '__main__':
    unittest.main()
