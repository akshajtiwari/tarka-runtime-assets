from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from catalog import source_references
from components import installed
from licenses import identifiers


class MetadataTests(unittest.TestCase):
    def test_package_parser_stops_before_file_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / 'installed'
            database.write_text('P:tool\nV:1-r0\nL:MIT\no:source\nc:abc\nA:x86_64\nF:usr\nP:must-not-overwrite\n\n')
            record = installed(database)[0]
            self.assertEqual((record['name'], record['origin'], record['commit']), ('tool', 'source', 'abc'))

    def test_catalog_requires_corresponding_source(self):
        components = [{'origin': 'tool', 'commit': 'abc'}]
        with self.assertRaisesRegex(ValueError, 'Missing corresponding'):
            source_references(components, [], 'https://example.test/release')
        sources = [{'origin': 'tool', 'commit': 'abc', 'file': 'tool.zip'}]
        result = source_references(components, sources, 'https://example.test/release')
        self.assertEqual(result[0]['url'], 'https://example.test/release/tool.zip')

    def test_alpine_public_domain_and_deprecated_classpath_labels(self):
        self.assertEqual(identifiers('MIT AND Public Domain'), ['MIT', 'Public-Domain'])
        self.assertEqual(identifiers('GPL-2.0-with-classpath-exception'),
                         ['Classpath-exception-2.0', 'GPL-2.0-only'])

    def test_license_expressions_preserve_exceptions(self):
        self.assertEqual(identifiers('(GPL-2.0-or-later WITH Classpath-exception-2.0) OR MIT'),
                         ['Classpath-exception-2.0', 'GPL-2.0-or-later', 'MIT'])


if __name__ == '__main__':
    unittest.main()
