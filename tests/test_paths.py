from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from paths import validate_paths


class PathTests(unittest.TestCase):
    def test_rejects_ambiguous_and_traversal_names(self):
        for name in ('', '/etc/passwd', '../outside', 'a/../b', 'a//b', 'a/./b', 'a\\b', 'a\0b'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_paths({name: {'kind': 'file'}})

    def test_path_characters_and_bounds_match_native_installer(self):
        for name in ('a' + chr(92) + 'b', 'a' + chr(0) + 'b', 'x' * 4097, '/'.join(['x'] * 65)):
            with self.subTest(name=repr(name)), self.assertRaises(ValueError):
                validate_paths({name: {'kind': 'file'}})

    def test_rejects_overlong_symbolic_link_chains(self):
        links = {f'link{index}': {'kind': 'link', 'target': f'link{index + 1}'} for index in range(65)}
        with self.assertRaisesRegex(ValueError, 'chain exceeds'):
            validate_paths(links)

    def test_rejects_files_used_as_parent_directories(self):
        with self.assertRaisesRegex(ValueError, 'below a regular file'):
            validate_paths({'bin': {'kind': 'file'}, 'bin/tool': {'kind': 'file'}})

    def test_rejects_entries_below_links(self):
        with self.assertRaisesRegex(ValueError, 'below'):
            validate_paths({'usr': {'kind': 'link', 'target': '/outside'},
                            'usr/secret': {'kind': 'file'}})

    def test_rejects_link_escape_and_cycles(self):
        for links in ({'a': '../outside'}, {'a': 'b', 'b': 'a'},
                      {'a': '/b', 'b': '../../outside'}, {'a': 'a/child'}):
            with self.subTest(links=links), self.assertRaises(ValueError):
                validate_paths({name: {'kind': 'link', 'target': target} for name, target in links.items()})

    def test_allows_absolute_guest_links_and_relative_siblings(self):
        validate_paths({'bin': {'kind': 'link', 'target': '/usr/bin'},
                        'usr/bin/java': {'kind': 'link', 'target': '../lib/jvm/bin/java'}})


if __name__ == '__main__':
    unittest.main()
