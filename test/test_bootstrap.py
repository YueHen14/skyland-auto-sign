"""Exercise the real bootstrap using local fake curl/binary commands."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipIf(sys.platform == 'win32', 'POSIX runtime protocol is checked by Linux CI')
class BootstrapTest(unittest.TestCase):
    def run_bootstrap(self, exit_status):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'index').mkdir()
            (folder / 'bin').mkdir()
            (folder / 'temp').mkdir()
            bootstrap = folder / 'bootstrap'
            shutil.copyfile(ROOT / 'cloud_functions' / 'bootstrap', bootstrap)
            program = folder / 'index' / 'index'
            program.write_text('#!/bin/sh\nprintf \'{"success":true}\\n\'\nexit ' + str(exit_status) + '\n')
            program.chmod(0o755)
            curl = folder / 'bin' / 'curl'
            curl.write_text('''#!/bin/sh
headers=''
output=''
while [ "$#" -gt 0 ]; do
    case "$1" in
        -D) headers="$2"; shift ;;
        -o) output="$2"; shift ;;
    esac
    url="$1"
    shift
done
case "$url" in
    */request)
        printf 'HTTP/1.1 200 OK\\r\\nX-Cff-Request-Id: fake-request-id\\r\\n' > "$headers"
        printf '{}' > "$output"
        ;;
    *)
        printf '%s' "$url" > "$AUDIT_PROTOCOL_RESULT"
        kill -TERM "$PPID"
        ;;
esac
''')
            curl.chmod(0o755)
            result_file = folder / 'protocol-result'
            env = dict(os.environ, RUNTIME_API_ADDR='runtime.invalid:1234',
                       RUNTIME_CODE_ROOT=str(folder), AUDIT_PROTOCOL_RESULT=str(result_file),
                       PATH=str(folder / 'bin') + os.pathsep + os.environ['PATH'], TMPDIR=str(folder / 'temp'))
            result = subprocess.run(['sh', str(bootstrap)], cwd='/', env=env,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list((folder / 'temp').iterdir()), [])
            return result_file.read_text()

    def test_success_uses_response_endpoint(self):
        self.assertTrue(self.run_bootstrap(0).endswith('/response/fake-request-id'))

    def test_failure_uses_error_endpoint(self):
        self.assertTrue(self.run_bootstrap(1).endswith('/error/fake-request-id'))
