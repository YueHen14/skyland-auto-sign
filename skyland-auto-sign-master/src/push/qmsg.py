import logging
import os
import re
from datetime import date
from typing import Tuple

import requests


def push_qmsg(all_logs: list[str]):
    # === QMSG 推送（可选，通过环境变量控制） ===
    # 在本地或 GitHub Actions 设置：
    #   QMSG_TOKEN: 必填
    #   QQ: 可选，指定要接收消息的QQ号或者QQ群。多个以英文逗号分割，例如：12345,12346。
    #   BOT： 可选，机器人的QQ号。
    token = os.environ.get('QMSG_TOKEN', '').strip()
    qq = os.environ.get('QQ', '').strip()
    bot = os.environ.get('BOT', '').strip()
    if not token:
        return
    
    title = f'森空岛自动签到结果 - {date.today().strftime("%Y-%m-%d")}'
    desp = '\n'.join(all_logs) if all_logs else '今日无可用账号或无输出'
    api = f"https://qmsg.zendee.cn/jsend/{token}" #私聊
    #api = f"https://qmsg.zendee.cn/jgroup/{token}" #群聊
    payload = {
        "msg": f"{title}\n{desp}",
        "qq": qq,
        "bot": bot,
    }

    try:
        r = requests.post(api, json=payload)
        ok = (r.status_code == 200)
        if not ok:
            logging.error(f"qmsg推送失败,http代码{r.status_code},{r.text}")
    except Exception as e:
        logging.error("qmsg推送失败", exc_info=e)