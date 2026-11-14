import logging

from safe_logging import redact


def check_response(response, channel, field, expected):
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError(f'{channel} 返回格式不正确')
    if data.get(field) != expected:
        message = data.get('message') or data.get('msg') or '未知业务错误'
        logging.error('%s 推送请求被拒绝：%s', channel, redact(message))
        return False
    logging.info('%s 推送请求已被服务端接受', channel)
    return True
