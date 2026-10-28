import json
from pathlib import Path
import tempfile
import unittest

from candidate_build_fixtures import COMMIT, REPOSITORY, RUN_ID, VERSION
from candidate_fixtures import make_candidate, write_checksums, write_json
from candidate_files import verify_candidate


def verify(folder):
    return verify_candidate(folder, REPOSITORY, VERSION, RUN_ID, COMMIT)


class CandidateFileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        make_candidate(self.folder)

    def test_complete_flat_candidate_is_accepted(self):
        files = verify(self.folder)
        self.assertEqual(set(files), set(self.folder.iterdir()))

    def test_extra_files_and_directories_fail_even_with_matching_checksums(self):
        (self.folder / 'credentials.json').write_text('must never publish')
        write_checksums(self.folder)
        with self.assertRaisesRegex(ValueError, 'allowlist'):
            verify(self.folder)
        (self.folder / 'credentials.json').unlink()
        (self.folder / 'nested').mkdir()
        with self.assertRaisesRegex(ValueError, 'flat regular'):
            verify(self.folder)

    def test_symlinks_and_oversized_files_are_refused_before_reading_payloads(self):
        path = self.folder / 'base-x86_64.zip'
        path.unlink()
        path.symlink_to('/etc/passwd')
        with self.assertRaisesRegex(ValueError, 'flat regular'):
            verify(self.folder)
        path.unlink()
        with path.open('wb') as stream:
            stream.truncate(2 * 1024 ** 3 + 1)
        with self.assertRaisesRegex(ValueError, 'size limit'):
            verify(self.folder)

    def test_changed_payload_and_missing_duplicate_or_unsafe_checksum_entries_fail(self):
        path = self.folder / 'base-x86_64.zip'
        path.write_bytes(b'changed runtime')
        with self.assertRaisesRegex(ValueError, 'checksum differs'):
            verify(self.folder)
        write_checksums(self.folder)
        sums = self.folder / 'SHA256SUMS'
        original = sums.read_text()
        for text in [original.split('\n', 1)[1], original + original.splitlines()[0] + '\n',
                     original + 'a' * 64 + '  ../escape\n']:
            sums.write_text(text)
            with self.subTest(text=text[-80:]), self.assertRaises(ValueError):
                verify(self.folder)

    def test_rehashed_catalog_and_provenance_cannot_point_to_another_build(self):
        provenance = json.loads((self.folder / 'build-source.json').read_text())
        for key, value in [('commit', 'b' * 40), ('repository', 'owner/private-app'),
                           ('buildUrl', 'https://github.com/owner/assets/actions/runs/999')]:
            write_json(self.folder, 'build-source.json', dict(provenance, **{key: value}))
            write_checksums(self.folder)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'provenance'):
                verify(self.folder)
        write_json(self.folder, 'build-source.json', provenance)
        catalog = json.loads((self.folder / 'catalog.json').read_text())
        catalog['version'] = 'other'
        write_json(self.folder, 'catalog.json', catalog)
        write_checksums(self.folder)
        with self.assertRaisesRegex(ValueError, 'catalog version'):
            verify(self.folder)

    def test_duplicate_packs_and_rehashed_source_reference_changes_are_refused(self):
        original = json.loads((self.folder / 'catalog.json').read_text())
        catalog = json.loads(json.dumps(original))
        catalog['packs'][1] = catalog['packs'][0]
        write_json(self.folder, 'catalog.json', catalog)
        write_checksums(self.folder)
        with self.assertRaisesRegex(ValueError, 'eight runtime packs'):
            verify(self.folder)
        original['packs'][0]['sources'][0]['url'] = 'https://example.test/unreviewed.zip'
        write_json(self.folder, 'catalog.json', original)
        write_checksums(self.folder)
        with self.assertRaisesRegex(ValueError, 'source references'):
            verify(self.folder)


if __name__ == '__main__':
    unittest.main()
