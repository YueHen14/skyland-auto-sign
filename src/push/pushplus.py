import os
from datetime import date

import http_client as requests
from push.common import check_response
from safe_logging import register_secret


def push_pushplus(all_logs):
    token = os.environ.get('PUSHPLUS_TOKEN', '').strip()
    if not token:
        return None
    register_secret(token)
    payload = {'token': token, 'title': f'森空岛自动签到结果 - {date.today().isoformat()}',
               'content': '\n'.join(all_logs) or '今日无可用账号或无输出',
               'topic': os.environ.get('TOPIC', '').strip(), 'template': 'txt'}
    return check_response(requests.post('https://www.pushplus.plus/send', json=payload),
                          'PushPlus', 'code', 200)
