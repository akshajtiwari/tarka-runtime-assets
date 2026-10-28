import io
import json
from pathlib import Path
import sys
import unittest
import zipfile
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from verify_packs import read_manifest


class VerificationTests(unittest.TestCase):
    def test_rejects_unlisted_payloads_and_duplicate_paths(self):
        for duplicate in (False, True):
            stream = io.BytesIO()
            manifest = {'format': 1, 'directories': [], 'links': [],
                        'files': [{'path': 'bin/tool'}] * (2 if duplicate else 1)}
            with zipfile.ZipFile(stream, 'w') as archive:
                archive.writestr('manifest.json', json.dumps(manifest))
                archive.writestr('files/bin/tool', 'tool')
                archive.writestr('unlisted', 'malicious')
            stream.seek(0)
            with zipfile.ZipFile(stream) as archive, self.assertRaises(ValueError):
                read_manifest(archive)

    def test_requires_manifest_first(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('files/bin/tool', 'tool')
            archive.writestr('manifest.json', '{}')
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive, self.assertRaisesRegex(ValueError, 'misplaced'):
            read_manifest(archive)


if __name__ == '__main__':
    unittest.main()
