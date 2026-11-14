import os
from datetime import date
from urllib.parse import quote

import http_client as requests
from push.common import check_response
from safe_logging import register_secret


def push_qmsg(all_logs):
    token = os.environ.get('QMSG_TOKEN', '').strip()
    if not token:
        return None
    register_secret(token)
    title = f'森空岛自动签到结果 - {date.today().isoformat()}'
    payload = {'msg': title + '\n' + ('\n'.join(all_logs) or '今日无可用账号或无输出'),
               'qq': os.environ.get('QQ', '').strip(), 'bot': os.environ.get('BOT', '').strip()}
    api = f'https://qmsg.zendee.cn/jsend/{quote(token, safe="")}'
    return check_response(requests.post(api, json=payload), 'Qmsg', 'success', True)
