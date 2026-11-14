"""Smoke-check the actual frozen program without making a sign-in request."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / 'dist' / 'cloud_functions'
ARCHIVE = PACKAGE.with_suffix('.zip')


def check():
    with zipfile.ZipFile(ARCHIVE) as archive:
        names = archive.namelist()
        assert 'bootstrap' in names and 'index/index' in names
        assert archive.getinfo('bootstrap').external_attr >> 16 & 0o111
        assert archive.getinfo('index/index').external_attr >> 16 & 0o111
        assert archive.read('INPUT_HYPERGRYPH_TOKEN.txt') == b''
        assert not any(Path(name).name in {'config.ini', 'TOKEN.txt', '.env'} for name in names)
        assert b'\r\n' not in archive.read('bootstrap')
        assert not any('__pycache__' in name for name in names)
    env = {key: value for key, value in os.environ.items()
           if key not in {'SC3_SENDKEY', 'PUSHPLUS_TOKEN', 'QMSG_TOKEN', 'SKYLAND_PUSH_CONFIG'}}
    env.update(TOKEN='', RUNTIME_CODE_ROOT=str(PACKAGE), PYTHONIOENCODING='utf-8')
    with tempfile.TemporaryDirectory() as directory:
        result = subprocess.run([str(PACKAGE / 'index' / 'index')], cwd=directory,
                                env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 1, result.stderr
    payload = json.loads(result.stdout)
    assert payload['errorType'] == 'SignInFailed'
    assert payload['result']['success'] is False
    print('Frozen program, ZIP layout, executable modes and credential exclusions verified')


if __name__ == '__main__':
    check()
