import hashlib
import hmac
import json
import logging
import os.path
import threading
import time
from getpass import getpass
from urllib import parse

import requests

from SecuritySm import get_d_id

token_save_name = 'TOKEN.txt'
app_code = '4ca99fa6b56cc2ba'
token_env = os.environ.get('TOKEN')
# 现在想做什么？
current_type = os.environ.get('SKYLAND_TYPE')

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
    'dId': get_d_id(),
    'X-Requested-With': 'com.hypergryph.skland'
}

# 签名请求头一定要这个顺序，否则失败
# timestamp是必填的,其它三个随便填,不要为none即可
header_for_sign = {
    'platform': '3',
    'timestamp': '',
    'dId': header_login['dId'],
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
    logging.info(f'算出签名: {md5}')
    return md5, header_ca


def get_sign_header(url: str, method, body, h):
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
    resp = requests.post(login_code_url, json={'phone': phone, 'type': 2}, headers=header_login).json()
    if resp.get("status") != 0:
        raise Exception(f"发送手机验证码出现错误：{resp['msg']}")
    code = input("请输入手机验证码：")
    r = requests.post(token_phone_code_url, json={"phone": phone, "code": code}, headers=header_login).json()
    return get_token(r)


def login_by_token():
    token_code = input("请输入（登录森空岛电脑官网后请访问这个网址：https://web-api.skland.com/account/info/hg）:")
    return parse_user_token(token_code)


def parse_user_token(t):
    try:
        t = json.loads(t)
        return t['data']['content']
    except:
        pass
    return t


def login_by_password():
    phone = input('请输入手机号码：')
    password = getpass('请输入密码(不会显示在屏幕上面)：')
    r = requests.post(token_password_url, json={"phone": phone, "password": password}, headers=header_login).json()
    return get_token(r)


def get_cred_by_token(token):
    grant_code = get_grant_code(token)
    return get_cred(grant_code)


def get_token(resp):
    if resp.get('status') != 0:
        raise Exception(f'获得token失败：{resp["msg"]}')
    return resp['data']['token']


def get_grant_code(token):
    response = requests.post(grant_code_url, json={
        'appCode': app_code,
        'token': token,
        'type': 0
    }, headers=header_login)
    resp = response.json()
    if response.status_code != 200:
        raise Exception(f'获得认证代码失败：{resp}')
    if resp.get('status') != 0:
        raise Exception(f'获得认证代码失败：{resp["msg"]}')
    return resp['data']['code']


def get_cred(grant):
    resp = requests.post(cred_code_url, json={
        'code': grant,
        'kind': 1
    }, headers=header_login).json()
    if resp['code'] != 0:
        raise Exception(f'获得cred失败：{resp["message"]}')
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
        logging.error(f"请求角色列表出现问题：{resp['message']}")
        if resp.get('message') == '用户未登录':
            logging.error(f'用户登录可能失效了，请重新运行此程序！')
            os.remove(token_save_name)
            return []
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
        return [
            f'[{game_name}]角色{nickname}({channel})签到失败了！原因：{resp["message"]}']
    result = ''
    awards = resp['data']['awards']
    for j in awards:
        res = j['resource']
        result += f'{res["name"]}×{j.get("count") or 1}'
    return [f'[{game_name}]角色{nickname}({channel})签到成功，获得了{result}']


def sign_for_endfield(data: dict):
    roles: list[dict] = data.get('roles')
    game_name = data.get('gameName')
    channel = data.get("channelName")
    result = []
    for i in roles:
        nickname = i.get('nickname') or ''
        resp = do_sign_for_endfield(i)
        j = resp.json()
        if j['code'] != 0:
            result.append(f'[{game_name}]角色{nickname}({channel})签到失败了！原因:{j["message"]}')
        else:
            awards_result = []
            result_data: dict = j['data']
            result_info_map: dict = result_data['resourceInfoMap']
            for a in result_data['awardIds']:
                award_id = a['id']
                awards = result_info_map[award_id]
                award_name = awards['name']
                award_count = awards['count']
                awards_result.append(f'{award_name}×{award_count}')

            result.append(f'[{game_name}]角色{nickname}({channel})签到成功，获得了:{",".join(awards_result)}')
    return result


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
    success = True
    logs_out = []  # 新增：用于 Server酱³ 的汇总文本
    for i in characters:
        app_code = i['appCode']
        msg = None
        if app_code == 'arknights':
            msg = sign_for_arknights(i)
        elif app_code == 'endfield':
            msg = sign_for_endfield(i)
        logging.info(msg)

        logs_out.extend(msg)

    return success, logs_out


def save(token):
    with open(token_save_name, 'w') as f:
        f.write(token)
    logging.info(
        f'您的鹰角网络通行证保存在{token_save_name}, 打开这个可以把它复制到云函数服务器上执行!\n双击添加账号即可再次添加账号')


def read(path):
    if not os.path.exists(token_save_name):
        return []
    v = []
    with open(path, 'r', encoding='utf-8') as f:
        for i in f.readlines():
            i = i.strip()
            i and i not in v and v.append(i)
    return v


def read_from_env():
    v = []
    token_list = token_env.split(',')
    for i in token_list:
        i = i.strip()
        if i and i not in v:
            v.append(parse_user_token(i))
    logging.info(f'从环境变量中读取到{len(v)}个token...')
    return v


def init_token():
    if token_env:
        logging.info('使用环境变量里面的token')
        # 对于github action,不需要存储token,因为token在环境变量里
        return read_from_env()
    tokens = []
    tokens.extend(read(token_save_name))
    add_account = current_type == 'add_account'
    if add_account:
        logging.info('！！！您启用了添加账号模式，将不会签到！！！')
    if len(tokens) == 0 or add_account:
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


def start():
    token = init_token()
    success = True
    all_logs = []  # 新增：汇总所有账号/角色的输出
    for i in token:
        try:
            sign_success, logs_out = do_sign(get_cred_by_token(i))
            all_logs.extend(logs_out)
            if not sign_success:
                success = False
        except Exception as ex:
            err = f'签到失败，原因：{str(ex)}'
            logging.error(err, exc_info=ex)
            all_logs.append(err)
            success = False
    logging.info("签到完成！")

    return success, all_logs
