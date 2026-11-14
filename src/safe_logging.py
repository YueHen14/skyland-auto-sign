"""Shared credential redaction for logs, errors and notification summaries."""
import logging
import os
import threading
import traceback
from urllib.parse import quote, quote_plus

_secrets = set()
_lock = threading.Lock()


def register_secret(value):
    if isinstance(value, str) and value:
        with _lock:
            _secrets.update((value, quote(value, safe=''), quote_plus(value)))
    return value


def redact(value):
    text = str(value)
    for key in ('TOKEN', 'SC3_SENDKEY', 'PUSHPLUS_TOKEN', 'PUSHPLUSH_TOKEN', 'QMSG_TOKEN'):
        register_secret(os.environ.get(key))
    with _lock:
        secrets = sorted(_secrets, key=len, reverse=True)
    for secret in secrets:
        text = text.replace(secret, '*****')
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        if record.exc_info:
            message += '\n' + ''.join(traceback.format_exception(*record.exc_info))
            record.exc_info = None
        record.exc_text = None
        record.msg = redact(message)
        record.args = ()
        if record.stack_info:
            record.stack_info = redact(record.stack_info)
        return True
