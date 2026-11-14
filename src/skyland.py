import hashlib
import hmac
import json
import logging
import os.path
import sys
import tempfile
import threading
import time
from getpass import getpass
from urllib import parse
from pathlib import Path

import http_client as requests
from safe_logging import redact, register_secret

from SecuritySm import get_d_id

token_save_name = 'TOKEN.txt'
app_code = '4ca99fa6b56cc2ba'
_device_lock = threading.Lock()

http_local = threading.local()
header = {
    'cred': '',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-A5560 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Safari/537.36; SKLand/1.52.1',
    'Accept-Encoding': 'gzip',
    'Connection': 'close',
    'X-Requested-With': 'com.hypergryph.skland'
}
header_login = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-A5560 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/101.0.4951.61 Safari/537.36; SKLand/1.52.1',
    'Accept-Encoding': 'gzip',
    'Connection': 'close',
    'dId': '',
    'X-Requested-With': 'com.hypergryph.skland'
}

# 签名请求头一定要这个顺序，否则失败
# timestamp是必填的,其它三个随便填,不要为none即可
header_for_sign = {
    'platform': '3',
    'timestamp': '',
    'dId': '',
    'vName': '1.0.0'
}

# 签到url
sign_url_mapping = {
    'arknights': 'https://zonai.skland.com/api/v1/game/attendance',
    'endfield': 'https://zonai.skland.com/web/v1/game/endfield/attendance'
}

# 绑定的角色url
binding_url = "https://zonai.skland.com/api/v1/game/player/binding"
# 验证码url
login_code_url = "https://as.hypergryph.com/general/v1/send_phone_code"
# 验证码登录
token_phone_code_url = "https://as.hypergryph.com/user/auth/v2/token_by_phone_code"
# 密码登录
token_password_url = "https://as.hypergryph.com/user/auth/v1/token_by_phone_password"
# 使用token获得认证代码
grant_code_url = "https://as.hypergryph.com/user/oauth2/v2/grant"
# 使用认证代码获得cred
cred_code_url = "https://zonai.skland.com/web/v1/user/auth/generate_cred_by_code"
# refresh
refresh_token_url = "https://zonai.skland.com/web/v1/auth/refresh"


def get_login_header():
    # Importing this module must not perform network I/O.
    with _device_lock:
        if not header_login['dId']:
            header_login['dId'] = get_d_id()
            header_for_sign['dId'] = header_login['dId']
    return header_login.copy()


def generate_signature(path, body_or_query):
    """
    获得签名头
    接口地址+方法为Get请求？用query否则用body+时间戳+ 请求头的四个重要参数（dId，platform，timestamp，vName）.toJSON()
    将此字符串做HMAC加密，算法为SHA-256，密钥token为请求cred接口会返回的一个token值
    再将加密后的字符串做MD5即得到sign
    :param path: 请求路径（不包括网址）
    :param body_or_query: 如果是GET，则是它的query。POST则为它的body
    :return: 计算完毕的sign
    """
    # 总是说请勿修改设备时间，yj服务器似乎修复了，原始时间戳测试可以正常使用 
    t = str(int(time.time()))
    token = http_local.token.encode('utf-8')
    header_ca = json.loads(json.dumps(header_for_sign))
    header_ca['timestamp'] = t
    header_ca_str = json.dumps(header_ca, separators=(',', ':'))
    s = path + body_or_query + t + header_ca_str
    hex_s = hmac.new(token, s.encode('utf-8'), hashlib.sha256).hexdigest()
    md5 = hashlib.md5(hex_s.encode('utf-8')).hexdigest().encode('utf-8').decode('utf-8')
    return md5, header_ca


def get_sign_header(url: str, method, body, h):
    h = h.copy()
    p = parse.urlparse(url)
    if method.lower() == 'get':
        h['sign'], header_ca = generate_signature(p.path, p.query)
    else:
        h['sign'], header_ca = generate_signature(p.path, json.dumps(body) if body is not None else '')
    for i in header_ca:
        h[i] = header_ca[i]
    return h


def login_by_code():
    phone = input('请输入手机号码：')
    resp = requests.post(login_code_url, json={'phone': phone, 'type': 2}, headers=get_login_header()).json()
    if resp.get("status") != 0:
        raise Exception(f"发送手机验证码出现错误：{resp['msg']}")
    code = input("请输入手机验证码：")
    register_secret(code)
    r = requests.post(token_phone_code_url, json={"phone": phone, "code": code}, headers=get_login_header()).json()
    return get_token(r)


def login_by_token():
    token_code = input("请输入（登录森空岛电脑官网后请访问这个网址：https://web-api.skland.com/account/info/hg）:")
    return parse_user_token(token_code)


def parse_user_token(t):
    if not isinstance(t, str):
        raise ValueError('Token 必须是字符串')
    t = t.strip()
    try:
        value = json.loads(t)
    except json.JSONDecodeError:
        if t.startswith(('{', '[')):
            raise ValueError('Token JSON 格式不正确') from None
        return register_secret(t)
    if isinstance(value, str):
        return register_secret(value.strip())
    if isinstance(value, dict) and isinstance(value.get('data'), dict):
        content = value['data'].get('content')
        if isinstance(content, str) and content.strip():
            return register_secret(content.strip())
    raise ValueError('Token JSON 必须包含字符串 data.content')


def parse_tokens(text):
    """Accept raw comma/newline tokens, one account JSON, or a JSON list."""
    if isinstance(text, (list, tuple)):
        values = text
    else:
        text = text.strip()
        if not text:
            return []
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            values = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                values.extend([line] if line.startswith(('{', '[', '"')) else line.split(','))
        else:
            values = value if isinstance(value, list) else [value]
    result = []
    for value in values:
        if isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False)
        token = parse_user_token(value)
        if token and token not in result:
            result.append(token)
    return result


def login_by_password():
    phone = input('请输入手机号码：')
    password = getpass('请输入密码(不会显示在屏幕上面)：')
    register_secret(password)
    r = requests.post(token_password_url, json={"phone": phone, "password": password}, headers=get_login_header()).json()
    return get_token(r)


def get_cred_by_token(token):
    grant_code = get_grant_code(token)
    return get_cred(grant_code)


def get_token(resp):
    if resp.get('status') != 0:
        raise Exception(f'获得token失败：{resp["msg"]}')
    return register_secret(resp['data']['token'])


def get_grant_code(token):
    register_secret(token)
    response = requests.post(grant_code_url, json={
        'appCode': app_code,
        'token': token,
        'type': 0
    }, headers=get_login_header())
    resp = response.json()
    if response.status_code != 200:
        raise Exception(f'获得认证代码失败：HTTP {response.status_code}')
    if resp.get('status') != 0:
        raise Exception(f'获得认证代码失败：{resp["msg"]}')
    return register_secret(resp['data']['code'])


def get_cred(grant):
    resp = requests.post(cred_code_url, json={
        'code': grant,
        'kind': 1
    }, headers=get_login_header()).json()
    if resp['code'] != 0:
        raise Exception(f'获得cred失败：{resp["message"]}')
    register_secret(resp['data']['cred'])
    register_secret(resp['data']['token'])
    return resp['data']


def refresh_token():
    headers = get_sign_header(refresh_token_url, 'get', None, http_local.header)
    resp = requests.get(refresh_token_url, headers=headers).json()
    if resp.get('code') != 0:
        raise Exception(f'刷新token失败:{resp["message"]}')
    http_local.token = resp['data']['token']


def get_binding_list():
    v = []
    resp = requests.get(binding_url, headers=get_sign_header(binding_url, 'get', None, http_local.header)).json()

    if resp['code'] != 0:
        raise RuntimeError(f"请求角色列表失败：{resp.get('message', '未知错误')}；请检查账号凭据")
    for i in resp['data']['list']:
        # 也许有些游戏没有签到功能？
        if i.get('appCode') not in ('arknights', 'endfield'):
            continue
        for j in i.get('bindingList'):
            j['appCode'] = i['appCode']
        v.extend(i['bindingList'])
    return v


def sign_for_arknights(data: dict):
    # 返回是否成功，消息
    body = {
        'gameId': data.get('gameId'),
        'uid': data.get('uid')
    }
    url = sign_url_mapping['arknights']
    headers = get_sign_header(url, 'post', body, http_local.header)
    resp = requests.post(url, headers=headers, json=body).json()
    game_name = data.get('gameName')
    channel = data.get("channelName")
    nickname = data.get('nickName') or ''
    if resp.get('code') != 0:
        if already_signed(resp):
            return True, [f'[{game_name}]角色{nickname}({channel})今日已签到']
        return False, [
            f'[{game_name}]角色{nickname}({channel})签到失败了！原因：{resp["message"]}']
    result = ''
    awards = resp['data']['awards']
    for j in awards:
        res = j['resource']
        result += f'{res["name"]}×{j.get("count") or 1}'
    return True, [f'[{game_name}]角色{nickname}({channel})签到成功，获得了{result}']


def already_signed(resp):
    # Exact known messages only; unknown nonzero codes remain failures.
    return resp.get('message') in {'请勿重复签到！', '请勿重复签到', '今日已签到', '今天已经签到了'}


def sign_for_endfield(data: dict):
    roles = data.get('roles') or []
    game_name = data.get('gameName')
    channel = data.get("channelName")
    result = []
    success = True
    if not roles:
        return False, [f'[{game_name}]未找到可签到角色']
    for i in roles:
        nickname = i.get('nickname') or ''
        try:
            j = do_sign_for_endfield(i).json()
            if j['code'] != 0:
                if already_signed(j):
                    result.append(f'[{game_name}]角色{nickname}({channel})今日已签到')
                else:
                    success = False
                    result.append(f'[{game_name}]角色{nickname}({channel})签到失败了！原因:{j["message"]}')
            else:
                awards_result = []
                result_data = j['data']
                result_info_map = result_data['resourceInfoMap']
                for award in result_data['awardIds']:
                    resource = result_info_map[str(award['id'])]
                    awards_result.append(f'{resource["name"]}×{resource["count"]}')
                result.append(f'[{game_name}]角色{nickname}({channel})签到成功，获得了:{",".join(awards_result)}')
        except Exception as exc:
            success = False
            result.append(f'[{game_name}]角色{nickname}({channel})签到失败：{redact(exc)}')
    return success, result


def do_sign_for_endfield(role: dict):
    url = sign_url_mapping['endfield']
    headers = get_sign_header(url, 'post', None, http_local.header)
    headers.update({
        'Content-Type': 'application/json',
        # FIXME b服不知道是不是这样
        # gameid_roleid_serverid
        'sk-game-role': f'3_{role["roleId"]}_{role["serverId"]}',
        'referer': 'https://game.skland.com/',
        'origin': 'https://game.skland.com/'
    })
    return requests.post(url, headers=headers)


def do_sign(cred_resp):
    http_local.token = cred_resp['token']
    http_local.header = header.copy()
    http_local.header['cred'] = cred_resp['cred']
    characters = get_binding_list()
    if not characters:
        return False, ['未找到已绑定的可签到角色，请检查账号与游戏绑定']
    success = True
    logs_out = []  # 新增：用于 Server酱³ 的汇总文本
    for i in characters:
        app_code = i['appCode']
        try:
            if app_code == 'arknights':
                role_success, msg = sign_for_arknights(i)
            elif app_code == 'endfield':
                role_success, msg = sign_for_endfield(i)
            else:
                continue
        except Exception as exc:
            role_success = False
            msg = [f'[{i.get("gameName", app_code)}]角色签到失败：{redact(exc)}']
        success = success and role_success
        msg = [redact(line) for line in msg]
        for line in msg:
            logging.info(line)
        logs_out.extend(msg)

    return success, logs_out


def save(token):
    path = Path(os.environ.get('TOKEN_FILE') or token_save_name)
    # Replace atomically; mkstemp creates a private file on POSIX systems.
    fd, temporary = tempfile.mkstemp(prefix='.token-', dir=path.resolve().parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(token)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    logging.info(
        f'您的鹰角网络通行证保存在{token_save_name}, 打开这个可以把它复制到云函数服务器上执行!\n双击添加账号即可再次添加账号')


def read(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return parse_tokens(f.read())


def read_from_env():
    v = parse_tokens(os.environ.get('TOKEN', ''))
    logging.info(f'从环境变量中读取到{len(v)}个token...')
    return v


def init_token(interactive=None):
    if 'TOKEN' in os.environ:
        logging.info('使用环境变量里面的token')
        # 对于github action,不需要存储token,因为token在环境变量里
        return read_from_env()
    tokens = []
    tokens.extend(read(os.environ.get('TOKEN_FILE') or token_save_name))
    add_account = os.environ.get('SKYLAND_TYPE') == 'add_account'
    if add_account:
        logging.info('！！！您启用了添加账号模式，将不会签到！！！')
    if len(tokens) == 0 or add_account:
        if interactive is None:
            interactive = sys.stdin.isatty()
        if not interactive:
            raise ValueError('没有可用账号，请配置 TOKEN 环境变量或 TOKEN_FILE 文件')
        tokens.append(input_for_token())
        save('\n'.join(tokens))
    return [] if add_account else tokens


def input_for_token():
    print("请输入你需要做什么：")
    print("1.使用用户名密码登录（非常推荐）")
    print("2.使用手机验证码登录（非常推荐，但可能因为人机验证失败）")
    print("3.手动输入鹰角网络通行证账号登录")
    mode = input('请输入（1，2，3）：')
    if mode == '' or mode == '1':
        token = login_by_password()
    elif mode == '2':
        token = login_by_code()
    elif mode == '3':
        token = login_by_token()
    else:
        exit(-1)
    return token


def start(tokens=None, interactive=None):
    try:
        token = init_token(interactive) if tokens is None else parse_tokens(tokens)
    except Exception as exc:
        return False, [f'读取账号失败：{redact(exc)}']
    if not token:
        if os.environ.get('SKYLAND_TYPE') == 'add_account':
            return True, ['账号添加完成，本次不执行签到']
        return False, ['没有可用账号，请配置 TOKEN 环境变量或 TOKEN_FILE 文件']
    success = True
    all_logs = []  # 新增：汇总所有账号/角色的输出
    for i in token:
        try:
            sign_success, logs_out = do_sign(get_cred_by_token(i))
            all_logs.extend(logs_out)
            if not sign_success:
                success = False
        except Exception as ex:
            err = f'签到失败，原因：{redact(ex)}'
            logging.error(err)
            all_logs.append(err)
            success = False
    logging.info("签到完成！")

    return success, all_logs
