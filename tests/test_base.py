from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from build_packs import prepare_base


class BaseTests(unittest.TestCase):
    def test_root_home_and_optional_binutils_alias_are_prepared_idempotently(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'etc').mkdir()
            (root / 'usr/bin').mkdir(parents=True)
            (root / 'etc/passwd').write_text('root:x:0:0:root:/root:/bin/sh\n')
            (root / 'usr/bin/strings').symlink_to('/bin/busybox')
            prepare_base(root)
            prepare_base(root)
            self.assertEqual((root / 'etc/passwd').read_text(), 'root:x:0:0:root:/home/tarka:/bin/sh\n')
            self.assertFalse((root / 'usr/bin/strings').is_symlink())


if __name__ == '__main__':
    unittest.main()
