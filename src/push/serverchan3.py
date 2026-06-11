import logging
import os
import re
from datetime import date
from typing import Tuple

import requests


def _format_serverchan_desp(all_logs: list[str]) -> str:
    if not all_logs:
        return '今日无可用账号或无输出'

    lines: list[str] = []
    for item in all_logs:
        text = item.replace('\r\n', '\n')
        parts = text.split('\n\n')
        if not parts:
            lines.append('')
            continue
        lines.extend(parts)

    # Server酱 desp 使用 Markdown，单换行会折叠为一个空格，需要显式换行。
    return '  \n'.join(line.rstrip() for line in lines)


def push_serverchan3(all_logs: list[str]):
    # === Server酱³ 推送（可选，通过环境变量控制） ===
    # 在本地或 GitHub Actions 设置：
    #   SC3_SENDKEY: 必填

    sendkey = os.environ.get('SC3_SENDKEY', '').strip()
    if not sendkey:
        return

    title = f'森空岛自动签到结果 - {date.today().strftime("%Y-%m-%d")}'

    desp = _format_serverchan_desp(all_logs)

    api = f"https://sctapi.ftqq.com/{sendkey}.send"
    payload = {
        "title": title or "通知",
        "desp": desp or "",
    }
    # if tags:
    #     payload["tags"] = tags
    # if short:
    #     payload["short"] = short

    try:
        r = requests.post(api, json=payload)
        ok = (r.status_code == 200)
        if not ok:
            logging.error(f"serverchan推送失败,http代码{r.status_code},{r.text}")
    except Exception as e:
        logging.error("serverchan推送失败", exc_info=e)
