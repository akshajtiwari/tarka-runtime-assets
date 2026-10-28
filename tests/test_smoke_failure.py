import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class SmokeFailureTests(unittest.TestCase):
    def test_mount_failure_stops_before_chroot_or_cleanup(self):
        script = Path(__file__).parents[1] / 'scripts/smoke-inside.sh'
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            root = work / 'runtime'
            for name in ('etc', 'dev', 'proc'):
                (root / name).mkdir(parents=True)
            (work / 'fixtures').mkdir()
            (work / 'fixtures/smoke.sh').write_text('exit 0\n')
            commands = work / 'commands'
            commands.mkdir()
            (commands / 'mount').write_text('#!/bin/sh\necho mount-denied >&2\nexit 41\n')
            for name in ('chroot', 'umount'):
                (commands / name).write_text('#!/bin/sh\ntouch "$SMOKE_MARKER"\n')
            for command in commands.iterdir():
                command.chmod(0o755)
            marker = work / 'must-not-run'
            environment = dict(os.environ, PATH=str(commands) + ':' + os.environ['PATH'], SMOKE_MARKER=str(marker))
            result = subprocess.run(['sh', str(script), str(root)], cwd=work, env=environment,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 41)
            self.assertIn('mount-denied', result.stderr)
            self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
