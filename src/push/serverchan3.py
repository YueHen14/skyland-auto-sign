import os
import re
from datetime import date
from urllib.parse import quote

import http_client as requests
from push.common import check_response
from safe_logging import register_secret


def _format_serverchan_desp(all_logs):
    if not all_logs:
        return '今日无可用账号或无输出'
    lines = []
    for item in all_logs:
        lines.extend(item.replace('\r\n', '\n').splitlines())
    return '  \n'.join(line.rstrip() for line in lines)


def push_serverchan3(all_logs):
    sendkey = os.environ.get('SC3_SENDKEY', '').strip()
    if not sendkey:
        return None
    register_secret(sendkey)
    escaped = quote(sendkey, safe='')
    if sendkey.startswith('sctp'):
        match = re.fullmatch(r'sctp(\d+)t\S+', sendkey)
        if not match:
            raise ValueError('Server酱³ SendKey 格式不正确')
        api = f'https://{match.group(1)}.push.ft07.com/send/{escaped}.send'
    elif sendkey.startswith('SCT'):
        api = f'https://sctapi.ftqq.com/{escaped}.send'
    else:
        raise ValueError('SendKey 应以 sctp（Server酱³）或 SCT（Turbo）开头')
    payload = {'title': f'森空岛自动签到结果 - {date.today().isoformat()}',
               'desp': _format_serverchan_desp(all_logs)}
    return check_response(requests.post(api, json=payload), 'Server酱', 'code', 0)
