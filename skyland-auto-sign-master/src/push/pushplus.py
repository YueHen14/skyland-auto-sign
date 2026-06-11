import logging
import os
import re
from datetime import date
from typing import Tuple

import requests


def push_pushplus(all_logs: list[str]):
    # === PUSHPLUS 推送（可选，通过环境变量控制） ===
    # 在本地或 GitHub Actions 设置：
    #   PUSHPLUS_TOKEN: 推送密钥，必填
    #   TITLE：标题
    #   TOPIC：群组
    token = os.environ.get('PUSHPLUS_TOKEN', '').strip()
    if not token:
        return
    title = f'森空岛自动签到结果 - {date.today().strftime("%Y-%m-%d")}'
    topic = os.environ.get('TOPIC', '').strip()
    desp = '\n'.join(all_logs) if all_logs else '今日无可用账号或无输出'

    api = f"https://www.pushplus.plus/send?token={token}"
    payload = {
        "title": title or "通知",
        "content": desp or "",
        "topic": topic or "",
    }

    try:
        r = requests.post(api, json=payload)
        ok = (r.status_code == 200)
        if not ok:
            logging.error(f"pushplus推送失败,http代码{r.status_code},{r.text}")
    except Exception as e:
        logging.error("pushplus推送失败", exc_info=e)