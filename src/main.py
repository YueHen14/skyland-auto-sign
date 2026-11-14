import logging
import sys
from datetime import date
from pathlib import Path

import push
from http_client import env_bool
from safe_logging import RedactingFilter, redact
from skyland import start


def config_logger(log_to_file=True):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    if not logger.handlers:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        logger.addHandler(console)
    if log_to_file:
        Path('logs').mkdir(exist_ok=True)
        filename = str(Path('logs', date.today().isoformat() + '.log').resolve())
        if not any(isinstance(h, logging.FileHandler) and h.baseFilename == filename for h in logger.handlers):
            handler = logging.FileHandler(filename, encoding='utf-8')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    for handler in logger.handlers:
        if not any(isinstance(f, RedactingFilter) for f in handler.filters):
            handler.addFilter(RedactingFilter())


def run(tokens=None, interactive=None, log_to_file=True):
    config_logger(log_to_file)
    try:
        push.load_config_to_env()
        success, logs = start(tokens=tokens, interactive=interactive)
    except Exception as exc:
        success, logs = False, [f'启动失败：{redact(exc)}']
        logging.error(logs[0])
    logs = [redact(item) for item in logs]
    push_success = push.push(logs)
    return {'success': success, 'push_success': push_success, 'logs': logs}


def exit_code(result):
    failed = not result['success'] and env_bool('EXIT_WHEN_FAIL', default=True)
    push_failed = not result['push_success'] and env_bool('EXIT_WHEN_PUSH_FAIL')
    return int(failed or push_failed)


def main():
    return exit_code(run())


if __name__ == '__main__':
    raise SystemExit(main())
