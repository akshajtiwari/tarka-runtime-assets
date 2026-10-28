import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from build_metadata import main as write_metadata
from pack_tree import digest
from release_files import main as prepare_release


class ReleasePreparationTests(unittest.TestCase):
    def test_staged_uploads_are_flat_and_exclude_unlisted_workspace_files(self):
        with tempfile.TemporaryDirectory() as temporary, contextlib.chdir(temporary):
            root = Path('.artifacts/release')
            (root / 'sources').mkdir(parents=True)
            (root / 'sources/index.json').write_text('{"sources":[],"failures":[]}')
            names = ['catalog.json', 'licenses.zip', 'licenses.json', 'java-corresponding-sources.zip',
                     'java-sources.json', 'native-loader-corresponding-sources.zip', 'native-sources.json',
                     'manifests-arm64-v8a.json', 'manifests-x86_64.json']
            names.extend(f'{pack}-{abi}.zip' for pack in ('base', 'python', 'java', 'cpp')
                         for abi in ('arm64-v8a', 'x86_64'))
            for name in names:
                (root / name).write_bytes(b'public-asset')
            (root / 'sources/component.zip').write_bytes(b'component-source')
            (root / 'credentials.json').write_text('must never stage this')
            with contextlib.redirect_stdout(io.StringIO()):
                prepare_release(stage=True)
            output = Path('.artifacts/release-upload')
            self.assertTrue((output / 'component.zip').is_file())
            self.assertFalse((output / 'credentials.json').exists())
            self.assertFalse((output / 'sources').exists())
            for line in (output / 'SHA256SUMS').read_text().splitlines():
                expected, name = line.split('  ', 1)
                self.assertEqual(digest(output / name), expected)

    def test_build_revision_records_only_explicit_public_provenance(self):
        with tempfile.TemporaryDirectory() as temporary, contextlib.chdir(temporary):
            Path('.artifacts/release').mkdir(parents=True)
            environment = {'ASSET_REPOSITORY': 'owner/assets', 'ASSET_COMMIT': 'a' * 40,
                           'ASSET_RUN_ID': '123', 'PACK_VERSION': 'test', 'GH_TOKEN': 'do-not-record'}
            with patch.dict(os.environ, environment):
                write_metadata()
            record = json.loads(Path('.artifacts/release/build-source.json').read_text())
            self.assertEqual(record['sourceUrl'], 'https://github.com/owner/assets/tree/' + 'a' * 40)
            self.assertNotIn('do-not-record', json.dumps(record))
            with patch.dict(os.environ, dict(environment, ASSET_COMMIT='invalid')):
                with self.assertRaisesRegex(ValueError, 'source revision'):
                    write_metadata()


if __name__ == '__main__':
    unittest.main()
