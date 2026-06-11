import logging
import threading

import skyland

# 华为云本地文件在./code下面
file_save_token = './code/INPUT_HYPERGRYPH_TOKEN.txt'

logging.getLogger().setLevel(logging.INFO)


def read(path):
    v = []
    with open(path, 'r', encoding='utf-8') as f:
        for i in f.readlines():
            i = i.strip()
            i and i not in v and v.append(i)
    return v


def handler():
    token = read(file_save_token)
    if token:
        for i in range(1, len(token)):
            threading.Thread(target=start, args=(token[i],)).start()
        start(token[0])


def start(token):
    try:
        cred = skyland.get_cred_by_token(token)
        skyland.do_sign(cred)
    except Exception as ex:
        logging.error('签到完全失败了！：', exc_info=ex)


handler()
