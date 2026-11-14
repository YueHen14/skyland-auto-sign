"""FunctionGraph entry: shared sign-in, notifications and failure reporting."""
import json
import os
import sys
from pathlib import Path

from http_client import env_bool
from main import run
from safe_logging import redact


def default_token_path():
    if os.environ.get('RUNTIME_CODE_ROOT'):
        root = Path(os.environ['RUNTIME_CODE_ROOT'])
    elif getattr(sys, 'frozen', False):
        root = Path(sys.executable).resolve().parent.parent
    else:
        root = Path(__file__).resolve().parent.parent / 'cloud_functions'
    return root / 'INPUT_HYPERGRYPH_TOKEN.txt'


def run_cloud():
    previous = os.environ.get('TOKEN_FILE')
    if not previous:
        os.environ['TOKEN_FILE'] = str(default_token_path())
    try:
        return run(interactive=False, log_to_file=False)
    finally:
        if previous is None:
            os.environ.pop('TOKEN_FILE', None)
        else:
            os.environ['TOKEN_FILE'] = previous


def failed(result):
    return not result['success'] or (not result['push_success'] and env_bool('EXIT_WHEN_PUSH_FAIL'))


def handler(event=None, context=None):
    result = run_cloud()
    if failed(result):
        raise RuntimeError(redact('；'.join(result['logs']) or '推送请求失败'))
    return result


def main():
    try:
        result = run_cloud()
        if failed(result):
            payload = {'errorType': 'SignInFailed', 'errorMessage': '签到或通知失败，请查看结果', 'result': result}
            code = 1
        else:
            payload, code = result, 0
    except Exception as exc:
        payload = {'errorType': type(exc).__name__, 'errorMessage': redact(exc)}
        code = 1
    # stdout is the FunctionGraph response; all logging goes to stderr.
    print(json.dumps(payload, ensure_ascii=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
