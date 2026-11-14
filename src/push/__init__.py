import logging
import os
from configparser import ConfigParser
from pathlib import Path

from safe_logging import redact, register_secret
from push.serverchan3 import push_serverchan3
from push.pushplus import push_pushplus
from push.qmsg import push_qmsg

CONFIG_KEYS = {'SC3_SENDKEY', 'SC3_UID', 'PUSHPLUS_TOKEN', 'QMSG_TOKEN', 'TOPIC', 'QQ', 'BOT'}
PUSHERS = {'serverchan': push_serverchan3, 'pushplus': push_pushplus, 'qmsg': push_qmsg}


def load_config_to_env():
    """Environment variables take precedence over an optional untracked file."""
    config = ConfigParser(interpolation=None)
    path = Path(os.environ.get('SKYLAND_PUSH_CONFIG') or Path(__file__).with_name('config.ini'))
    if not path.exists():
        return
    config.read(path, encoding='utf-8')
    for section in config.sections():
        for option, value in config.items(section):
            key = option.upper()
            if key == 'PUSHPLUSH_TOKEN':
                key = 'PUSHPLUS_TOKEN'
                logging.warning('旧配置 PUSHPLUSH_TOKEN 已兼容，请改为 PUSHPLUS_TOKEN')
            if key not in CONFIG_KEYS:
                logging.warning('忽略未知推送配置项：%s', key)
                continue
            if value.strip():
                os.environ.setdefault(key, register_secret(value.strip()))


def push(all_logs):
    success = True
    logs = [redact(line) for line in all_logs]
    for name, pusher in PUSHERS.items():
        try:
            if pusher(logs) is False:
                success = False
        except Exception as exc:
            logging.error('[Push] %s 失败：%s', name, redact(exc))
            success = False
    return success
