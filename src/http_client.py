"""Bounded HTTPS requests shared by every deployment entry point."""
import os
from urllib.parse import urlsplit

import requests

DEFAULT_TIMEOUT = (5, 20)
TRUE_VALUES = {'1', 'true', 'yes', 'on'}
FALSE_VALUES = {'0', 'false', 'no', 'off', ''}


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    value = value.strip().lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise ValueError(f'{name} 必须填写 on/off、true/false 或 1/0')


def request(method, url, **kwargs):
    kwargs.setdefault('timeout', DEFAULT_TIMEOUT)
    kwargs.setdefault('verify', True)
    if kwargs['verify'] is False:
        raise ValueError('不允许关闭 HTTPS 证书校验，请配置受信任的 CA')
    if env_bool('USE_PROXY'):
        proxy = os.environ.get('PROXY_URL', 'http://localhost:8000').strip()
        if urlsplit(proxy).scheme not in ('http', 'https') or not urlsplit(proxy).hostname:
            raise ValueError('PROXY_URL 必须是有效的 HTTP/HTTPS 代理地址')
        kwargs['proxies'] = {'http': proxy, 'https': proxy}
    host = urlsplit(url).hostname or 'remote service'
    try:
        response = requests.request(method, url, **kwargs)
    except requests.RequestException as exc:
        raise RuntimeError(f'{host} 请求失败（{type(exc).__name__}）') from None
    if not 200 <= response.status_code < 300:
        raise RuntimeError(f'{host} 请求失败（HTTP {response.status_code}）')
    return response


def get(url, **kwargs):
    return request('GET', url, **kwargs)


def post(url, **kwargs):
    return request('POST', url, **kwargs)
