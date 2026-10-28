from pathlib import Path
import tempfile
import unittest
import zipfile
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from pack_tree import overlay, scan, verify_overlap, write_pack


class PackTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / 'root'
        self.root.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def test_zip_contains_regular_payload_and_links_only_in_manifest(self):
        (self.root / 'bin').mkdir()
        target = self.root / 'bin/tool'
        target.write_text('program')
        target.chmod(0o4755)
        (self.root / 'bin/alias').symlink_to('tool')
        output = Path(self.temporary.name) / 'base.zip'
        manifest, _ = write_pack(self.root, output, 'base', 'x86_64', 'test')
        self.assertEqual(manifest['files'][0]['mode'], 0o755)
        self.assertEqual(manifest['links'], [{'path': 'bin/alias', 'target': 'tool'}])
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(archive.namelist(), ['manifest.json', 'files/bin/tool'])
            self.assertEqual(archive.read('files/bin/tool'), b'program')
            self.assertEqual(archive.getinfo('files/bin/tool').external_attr >> 16 & 0o7777, 0o755)
        second = Path(self.temporary.name) / 'second.zip'
        write_pack(self.root, second, 'base', 'x86_64', 'test')
        self.assertEqual(output.read_bytes(), second.read_bytes())

    def test_overlay_rejects_mutating_or_deleting_base(self):
        (self.root / 'base').write_text('original')
        base = scan(self.root)
        (self.root / 'added').write_text('new')
        self.assertEqual(set(overlay(scan(self.root), base)), {'added'})
        (self.root / 'base').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'alters base'):
            overlay(scan(self.root), base)

    def test_optional_overlap_requires_identical_kind_mode_and_bytes(self):
        common = {'directories': [], 'links': [], 'files': [{'path': 'shared', 'sha256': 'a'}]}
        verify_overlap([common, common])
        other = {'directories': [], 'links': [], 'files': [{'path': 'shared', 'sha256': 'b'}]}
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            verify_overlap([common, other])

    def test_optional_overlap_rejects_cross_pack_link_traversal(self):
        link = {'directories': [], 'files': [], 'links': [{'path': 'usr', 'target': '/tmp'}]}
        file = {'directories': [], 'links': [], 'files': [{'path': 'usr/bin/tool', 'sha256': 'a'}]}
        with self.assertRaisesRegex(ValueError, 'below'):
            verify_overlap([link, file])


if __name__ == '__main__':
    unittest.main()
