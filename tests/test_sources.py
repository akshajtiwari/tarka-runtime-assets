from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import io
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from java_source_trees import declared_checksum
from java_sources import fetch


class SourceTests(unittest.TestCase):
    def test_debian_source_checksums_accept_header_whitespace_and_stop_at_next_field(self):
        text = 'Checksums-Sha256: \n abc 12 original.tar.gz\nFiles: \n wrong 12 original.tar.gz\n'
        self.assertEqual(declared_checksum(text, 'original.tar.gz'), 'abc')
        self.assertIsNone(declared_checksum(text, 'missing.tar.gz'))

    def test_source_cache_is_rejected_when_upstream_checksum_differs(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'source.zip'
            destination.write_text('corrupt')
            with patch('urllib.request.urlopen', return_value=io.BytesIO(b'wrong')):
                with self.assertRaisesRegex(ValueError, 'checksum differs'):
                    fetch('https://example.test/source.zip', destination, 'sha256')


if __name__ == '__main__':
    unittest.main()
