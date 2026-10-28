import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from catalog import ABIS, PACKS, main
from pack_tree import digest
from pack_fixtures import manifest, write_archive


class CatalogGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.output = Path(self.temporary.name)
        (self.output / 'sources').mkdir()
        (self.output / 'sources/index.json').write_text('{"sources":[],"failures":[]}')
        for name in ('native', 'java', 'licenses'):
            asset = self.output / (name + '.zip')
            asset.write_bytes(b'source-or-license')
            metadata = {'file': asset.name, 'sha256': digest(asset), 'bytes': asset.stat().st_size}
            filename = 'licenses.json' if name == 'licenses' else name + '-sources.json'
            (self.output / filename).write_text(json.dumps(metadata))
        for abi in ABIS:
            for pack_id in PACKS:
                write_archive(self.output / f'{pack_id}-{abi}.zip', manifest(pack_id, abi))

    def tearDown(self):
        self.temporary.cleanup()

    def test_valid_fixture_catalog_is_created(self):
        main('https://example.test/release', self.output)
        self.assertEqual(len(json.loads((self.output / 'catalog.json').read_text())['packs']), 8)

    def test_reviewer_unlisted_traversal_payload_cannot_get_a_catalog(self):
        write_archive(self.output / 'base-arm64-v8a.zip', manifest(), extra=True)
        with self.assertRaisesRegex(ValueError, 'differs from manifest'):
            main('https://example.test/release', self.output)
        self.assertFalse((self.output / 'catalog.json').exists())

    def test_identity_base_dependency_and_versions_must_match_filename_and_base(self):
        for key, value in [('id', 'cpp'), ('abi', 'x86_64'), ('baseVersion', None), ('version', 'different')]:
            record = manifest('python')
            record[key] = value
            write_archive(self.output / 'python-arm64-v8a.zip', record)
            with self.subTest(key=key), self.assertRaises(ValueError):
                main('https://example.test/release', self.output)
            self.assertFalse((self.output / 'catalog.json').exists())

    def test_payload_cannot_be_changed_and_given_a_fresh_catalog_hash(self):
        write_archive(self.output / 'base-arm64-v8a.zip', manifest(), b'evil')
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            main('https://example.test/release', self.output)
        self.assertFalse((self.output / 'catalog.json').exists())


if __name__ == '__main__':
    unittest.main()
