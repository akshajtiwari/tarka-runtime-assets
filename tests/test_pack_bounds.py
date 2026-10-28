import io
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from pack_fixtures import manifest, write_archive
from pack_manifest import MAX_FILE_BYTES, read_manifest, validate_archive_file
from pack_payload import copy_verified, verify_payload


class BoundTests(unittest.TestCase):
    def read(self, record, payload=b'tool'):
        stream = io.BytesIO()
        write_archive(stream, record, payload)
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            return read_manifest(archive)

    def test_reviewer_size_mismatch_is_rejected_before_extraction(self):
        record = manifest(payload=b'x')
        with self.assertRaisesRegex(ValueError, 'ZIP file size differs'):
            self.read(record, b'x' * 1024)

    def test_file_and_aggregate_limits_are_enforced_before_copying(self):
        record = manifest()
        record['files'][0]['size'] = MAX_FILE_BYTES + 1
        with self.assertRaisesRegex(ValueError, 'allowed size'):
            self.read(record)
        with patch('pack_manifest.MAX_PACK_BYTES', 3), self.assertRaisesRegex(ValueError, 'unpacked size'):
            self.read(manifest())

    def test_modes_special_zip_types_and_unreadable_directories_are_rejected(self):
        for mode in (-1, True, 0o4755):
            record = manifest()
            record['files'][0]['mode'] = mode
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'mode'):
                self.read(record)
        record = manifest()
        record['directories'] = [{'path': 'private', 'mode': 0o100}]
        with self.assertRaisesRegex(ValueError, 'Directory mode'):
            self.read(record)
        stream = io.BytesIO()
        write_archive(stream, manifest())
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            archive.infolist()[1].external_attr = (stat.S_IFLNK | 0o777) << 16
            with self.assertRaisesRegex(ValueError, 'regular files'):
                read_manifest(archive)

    def test_copy_bounds_declared_size_and_remaining_aggregate_while_reading(self):
        for remaining in (1, 20):
            output = io.BytesIO()
            with self.subTest(remaining=remaining), self.assertRaisesRegex(ValueError, 'exceeds'):
                copy_verified(io.BytesIO(b'long-payload'), output, manifest()['files'][0], remaining)
            self.assertLessEqual(len(output.getvalue()), min(remaining, 4))

    def test_packed_archive_and_dos_directory_flags_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / 'oversized.zip'
            archive_path.write_bytes(b'1234')
            with patch('pack_manifest.MAX_ARCHIVE_BYTES', 3), self.assertRaisesRegex(ValueError, 'Packed archive'):
                validate_archive_file(archive_path)
        stream = io.BytesIO()
        write_archive(stream, manifest())
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            archive.infolist()[1].external_attr |= 0x10
            with self.assertRaisesRegex(ValueError, 'regular files'):
                read_manifest(archive)

    def test_actual_payload_hash_is_verified(self):
        stream = io.BytesIO()
        write_archive(stream, manifest(), b'evil')
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            record = read_manifest(archive)
            with self.assertRaisesRegex(ValueError, 'hash differs'):
                verify_payload(archive, record)


if __name__ == '__main__':
    unittest.main()
