import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from native_sources import fetch_source


class NativeSourceTests(unittest.TestCase):
    def setUp(self):
        self.item = {'name': 'component', 'url': 'https://upstream.test/source.tar.gz',
                     'mirrors': ['https://mirror.test/source.tar.gz'],
                     'sha256': hashlib.sha256(b'original sources').hexdigest()}

    def test_gateway_failure_uses_identical_mirror_before_atomic_rename(self):
        error = urllib.error.HTTPError(self.item['url'], 504, 'timeout', {}, None)
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'source.tar.gz'
            with patch('native_sources.urllib.request.urlopen',
                       side_effect=[error, io.BytesIO(b'original sources')]) as request:
                fetch_source(self.item, destination)
            self.assertEqual(destination.read_bytes(), b'original sources')
            self.assertEqual(request.call_args.args[0], self.item['mirrors'][0])
            self.assertEqual(request.call_args.kwargs['timeout'], 20)
            self.assertFalse(destination.with_suffix('.part').exists())

    def test_mirror_cannot_replace_sources_with_different_content(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'source.tar.gz'
            with patch('native_sources.urllib.request.urlopen', return_value=io.BytesIO(b'wrong')):
                with self.assertRaisesRegex(ValueError, 'checksum differs'):
                    fetch_source(self.item, destination)
            self.assertFalse(destination.exists())
            self.assertFalse(destination.with_suffix('.part').exists())

    def test_network_retries_are_bounded_and_leave_no_partial_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'source.tar.gz'
            with patch('native_sources.urllib.request.urlopen', side_effect=TimeoutError('timeout')) as request:
                with patch('native_sources.time.sleep'):
                    with self.assertRaisesRegex(RuntimeError, 'Could not download'):
                        fetch_source(self.item, destination)
            self.assertEqual(request.call_count, 4)
            self.assertFalse(destination.exists())
            self.assertFalse(destination.with_suffix('.part').exists())

    def test_cached_source_is_still_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'source.tar.gz'
            destination.write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'checksum differs'):
                fetch_source(self.item, destination)


if __name__ == '__main__':
    unittest.main()
