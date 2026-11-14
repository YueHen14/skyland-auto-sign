"""Offline regression checks. All game and push HTTP requests are mocked."""
import contextlib
import importlib
import io
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

import requests
import http_client
import index
import main
import push
import skyland
import SecuritySm
from push import pushplus, qmsg, serverchan3
from safe_logging import RedactingFilter, register_secret

CRED = {'cred': 'FAKE_CRED_FOR_TESTS', 'token': 'FAKE_SIGNING_TOKEN_FOR_TESTS'}
ARK = {'appCode': 'arknights', 'gameName': '明日方舟', 'gameId': 1,
       'uid': 'FAKE_UID', 'nickName': '测试角色', 'channelName': '官服'}
END = {'appCode': 'endfield', 'gameName': '终末地', 'channelName': '官服',
       'roles': [{'roleId': 'ROLE_1', 'serverId': 'SERVER_1', 'nickname': '角色一'},
                 {'roleId': 'ROLE_2', 'serverId': 'SERVER_1', 'nickname': '角色二'}]}


def response(data, status=200):
    result = Mock()
    result.status_code = status
    result.json.return_value = data
    return result


class OfflineTest(unittest.TestCase):
    def setUp(self):
        system_env = {key: value for key, value in os.environ.items()
                      if key.upper() in {'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP'}}
        self.environ = patch.dict(os.environ, system_env, clear=True)
        self.environ.start()
        self.network = patch('requests.sessions.Session.request', side_effect=AssertionError('real network forbidden'))
        self.network.start()
        self.device = patch.object(skyland, 'get_d_id', return_value='B_FAKE_DEVICE')
        self.device.start()
        self.old_device = skyland.header_login['dId']
        self.old_sign_device = skyland.header_for_sign['dId']
        skyland.header_login['dId'] = ''
        skyland.header_for_sign['dId'] = ''
        self.handlers = list(logging.getLogger().handlers)

    def tearDown(self):
        for handler in list(logging.getLogger().handlers):
            if handler not in self.handlers:
                logging.getLogger().removeHandler(handler)
                handler.close()
        skyland.header_login['dId'] = self.old_device
        skyland.header_for_sign['dId'] = self.old_sign_device
        self.device.stop()
        self.network.stop()
        self.environ.stop()

    def test_imports_do_not_request_device_or_read_credentials(self):
        code = ('import sys,requests; from unittest.mock import patch; '
                'sys.path.insert(0,sys.argv[1]); '
                'p=patch("requests.sessions.Session.request",side_effect=AssertionError("network")); '
                'p.start(); import main,index; print("imported")')
        with tempfile.TemporaryDirectory() as folder:
            completed = subprocess.run([sys.executable, '-c', code, str(ROOT / 'src')],
                                       cwd=folder, capture_output=True, text=True, timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), 'imported')

    def test_tokens_accept_newlines_commas_and_deduplicate(self):
        self.assertEqual(skyland.parse_tokens('FAKE_ACCOUNT_ONE\r\nFAKE_ACCOUNT_TWO,FAKE_ACCOUNT_ONE'),
                         ['FAKE_ACCOUNT_ONE', 'FAKE_ACCOUNT_TWO'])

    def test_tokens_parse_full_pretty_account_json_before_splitting(self):
        value = {'status': 0, 'data': {'content': 'FAKE_ACCOUNT_ONE'}}
        self.assertEqual(skyland.parse_tokens(json.dumps(value, indent=2)), ['FAKE_ACCOUNT_ONE'])

    def test_tokens_accept_json_list_of_accounts_and_strings(self):
        text = json.dumps([{'data': {'content': 'FAKE_ACCOUNT_ONE'}}, 'FAKE_ACCOUNT_TWO'])
        self.assertEqual(skyland.parse_tokens(text), ['FAKE_ACCOUNT_ONE', 'FAKE_ACCOUNT_TWO'])

    def test_tokens_accept_one_json_per_line(self):
        text = '{"data":{"content":"FAKE_ACCOUNT_ONE"}}\n{"data":{"content":"FAKE_ACCOUNT_TWO"}}'
        self.assertEqual(skyland.parse_tokens(text), ['FAKE_ACCOUNT_ONE', 'FAKE_ACCOUNT_TWO'])

    def test_malformed_account_json_is_rejected(self):
        with self.assertRaises(ValueError):
            skyland.parse_tokens('{"data":')

    def test_read_uses_requested_path(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder, 'different-name.txt')
            file.write_text('FAKE_ACCOUNT_ONE\nFAKE_ACCOUNT_TWO', encoding='utf-8')
            self.assertEqual(len(skyland.read(file)), 2)

    def test_empty_or_missing_noninteractive_accounts_fail(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'TOKEN_FILE': str(Path(folder, 'missing'))}):
            success, logs = skyland.start(interactive=False)
        self.assertFalse(success)
        self.assertIn('没有可用账号', logs[0])

    def test_env_is_read_each_invocation(self):
        os.environ['TOKEN'] = 'FAKE_ACCOUNT_ONE'
        self.assertEqual(skyland.read_from_env(), ['FAKE_ACCOUNT_ONE'])
        os.environ['TOKEN'] = 'FAKE_ACCOUNT_TWO'
        self.assertEqual(skyland.read_from_env(), ['FAKE_ACCOUNT_TWO'])

    def test_device_crypto_works_with_locked_dependencies(self):
        with patch.object(http_client, 'post', return_value=response({'code': 1100, 'detail': {'deviceId': 'FAKE_DEVICE'}})) as post:
            self.assertEqual(SecuritySm.get_d_id(), 'BFAKE_DEVICE')
        self.assertEqual(post.call_args.args[0], SecuritySm.devices_info_url)
        self.assertNotIn('token', post.call_args.kwargs['json'])

    def test_unauthorized_response_preserves_all_saved_accounts(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder, 'TOKEN.txt')
            original = 'FAKE_ACCOUNT_ONE\nFAKE_ACCOUNT_TWO'
            file.write_text(original, encoding='utf-8')
            with patch.object(skyland, 'token_save_name', str(file)), \
                 patch.object(http_client, 'get', return_value=response({'code': 10002, 'message': '用户未登录'})):
                with self.assertRaisesRegex(RuntimeError, '请求角色列表失败'):
                    skyland.do_sign(CRED)
            self.assertEqual(file.read_text(encoding='utf-8'), original)

    def test_unauthorized_env_only_does_not_delete_missing_file(self):
        with patch.object(http_client, 'get', return_value=response({'code': 10002, 'message': '用户未登录'})), \
             patch.object(os, 'remove') as remove:
            with self.assertRaises(RuntimeError):
                skyland.do_sign(CRED)
        remove.assert_not_called()

    def test_arknights_business_failure_propagates(self):
        with patch.object(skyland, 'get_binding_list', return_value=[ARK]), \
             patch.object(skyland, 'get_cred_by_token', return_value=CRED), \
             patch.object(http_client, 'post', return_value=response({'code': 999, 'message': '拒绝签到'})):
            success, logs = skyland.start(tokens=['FAKE_ACCOUNT_ONE'])
        self.assertFalse(success)
        self.assertIn('拒绝签到', logs[0])

    def test_already_signed_is_success_without_hiding_unknown_errors(self):
        with patch.object(http_client, 'post', return_value=response({'code': 10001, 'message': '请勿重复签到！'})):
            skyland.http_local.token = CRED['token']
            skyland.http_local.header = {'cred': CRED['cred']}
            success, logs = skyland.sign_for_arknights(ARK)
        self.assertTrue(success)
        self.assertIn('已签到', logs[0])
        self.assertFalse(skyland.already_signed({'code': 999, 'message': '未知错误'}))

    def test_no_bound_roles_is_an_explicit_failure(self):
        with patch.object(skyland, 'get_binding_list', return_value=[]):
            success, logs = skyland.do_sign(CRED)
        self.assertFalse(success)
        self.assertIn('未找到', logs[0])

    def test_one_role_exception_keeps_previous_and_later_results(self):
        with patch.object(skyland, 'get_binding_list', return_value=[ARK, ARK, ARK]), \
             patch.object(skyland, 'sign_for_arknights', side_effect=[(True, ['first success']),
                              RuntimeError('second failed'), (True, ['third success'])]) as sign:
            success, logs = skyland.do_sign(CRED)
        self.assertFalse(success)
        self.assertEqual(sign.call_count, 3)
        self.assertEqual(logs[0], 'first success')
        self.assertEqual(logs[2], 'third success')

    def test_endfield_subrole_network_failure_does_not_skip_next(self):
        ok = {'code': 0, 'data': {'awardIds': [{'id': 1}], 'resourceInfoMap': {'1': {'name': '物品', 'count': 2}}}}
        with patch.object(skyland, 'do_sign_for_endfield', side_effect=[RuntimeError('offline'), response(ok)]) as sign:
            success, logs = skyland.sign_for_endfield(END)
        self.assertFalse(success)
        self.assertEqual(sign.call_count, 2)
        self.assertIn('物品×2', logs[1])

    def test_endfield_malformed_awards_does_not_discard_earlier_results(self):
        ok = {'code': 0, 'data': {'awardIds': [], 'resourceInfoMap': {}}}
        with patch.object(skyland, 'do_sign_for_endfield', side_effect=[response(ok), response({'code': 0, 'data': {}})]):
            success, logs = skyland.sign_for_endfield(END)
        self.assertFalse(success)
        self.assertEqual(len(logs), 2)
        self.assertIn('成功', logs[0])
        self.assertIn('失败', logs[1])

    def test_later_account_runs_after_first_account_login_failure(self):
        with patch.object(skyland, 'get_cred_by_token', side_effect=[RuntimeError('first failed'), CRED]), \
             patch.object(skyland, 'do_sign', return_value=(True, ['second success'])):
            success, logs = skyland.start(tokens=['FAKE_ACCOUNT_ONE', 'FAKE_ACCOUNT_TWO'])
        self.assertFalse(success)
        self.assertEqual(logs[-1], 'second success')

    def test_sign_headers_do_not_leak_between_games(self):
        skyland.http_local.token = CRED['token']
        original = {'cred': CRED['cred']}
        result = skyland.get_sign_header('https://example.invalid/path', 'post', None, original)
        result['sk-game-role'] = 'ROLE'
        self.assertEqual(original, {'cred': CRED['cred']})

    def test_signed_json_matches_requests_wire_encoding(self):
        body = {'gameId': 1, 'uid': 'FAKE_UID'}
        skyland.http_local.token = CRED['token']
        with patch.object(skyland, 'generate_signature', return_value=('SIGN', {})) as sign:
            skyland.get_sign_header('https://example.invalid/path', 'post', body, {})
        wire = requests.Request('POST', 'https://example.invalid/path', json=body).prepare().body
        self.assertEqual(sign.call_args.args[1].encode('utf-8'), wire)

    def test_false_proxy_strings_keep_certificate_verification(self):
        for value in ('false', 'off', '0', ''):
            with self.subTest(value=value), patch.dict(os.environ, {'USE_PROXY': value}), \
                 patch.object(requests, 'request', return_value=response({})) as request:
                http_client.get('https://example.invalid')
                self.assertNotIn('proxies', request.call_args.kwargs)
                self.assertIs(request.call_args.kwargs['verify'], True)
                self.assertEqual(request.call_args.kwargs['timeout'], (5, 20))

    def test_enabled_proxy_still_verifies_certificates(self):
        with patch.dict(os.environ, {'USE_PROXY': 'on', 'PROXY_URL': 'http://127.0.0.1:8001'}), \
             patch.object(requests, 'request', return_value=response({})) as request:
            http_client.post('https://example.invalid')
        self.assertEqual(request.call_args.kwargs['proxies']['https'], 'http://127.0.0.1:8001')
        self.assertIs(request.call_args.kwargs['verify'], True)

    def test_disabling_verification_is_rejected(self):
        with self.assertRaises(ValueError):
            http_client.post('https://example.invalid', verify=False)

    def test_transport_error_does_not_expose_secret_url(self):
        key = 'FAKE_KEY_FOR_NETWORK_ERROR'
        with patch.object(requests, 'request', side_effect=requests.ConnectionError('https://example.invalid/' + key)):
            with self.assertRaises(RuntimeError) as caught:
                http_client.get('https://example.invalid/' + key)
        self.assertNotIn(key, str(caught.exception))

    def test_non_success_http_status_is_rejected(self):
        with patch.object(requests, 'request', return_value=response({'token': 'HIDDEN'}, 500)):
            with self.assertRaisesRegex(RuntimeError, 'HTTP 500'):
                http_client.post('https://example.invalid')

    def test_sc3_uses_direct_endpoint_and_preserves_line_breaks(self):
        with patch.dict(os.environ, {'SC3_SENDKEY': 'sctp12345tFAKE_KEY_FOR_TESTS'}), \
             patch.object(http_client, 'post', return_value=response({'code': 0})) as post:
            self.assertTrue(serverchan3.push_serverchan3(['one\ntwo']))
        self.assertEqual(post.call_args.args[0], 'https://12345.push.ft07.com/send/sctp12345tFAKE_KEY_FOR_TESTS.send')
        self.assertEqual(post.call_args.kwargs['json']['desp'], 'one  \ntwo')

    def test_turbo_key_uses_legacy_endpoint(self):
        with patch.dict(os.environ, {'SC3_SENDKEY': 'SCT_FAKE_KEY_FOR_TESTS'}), \
             patch.object(http_client, 'post', return_value=response({'code': 0})) as post:
            self.assertTrue(serverchan3.push_serverchan3(['offline']))
        self.assertTrue(post.call_args.args[0].startswith('https://sctapi.ftqq.com/'))

    def test_invalid_sc3_key_never_requests(self):
        with patch.dict(os.environ, {'SC3_SENDKEY': 'sctpBAD'}), patch.object(http_client, 'post') as post:
            with self.assertRaises(ValueError):
                serverchan3.push_serverchan3(['offline'])
        post.assert_not_called()

    def test_push_business_rejections_are_not_accepted(self):
        cases = [(serverchan3.push_serverchan3, 'SC3_SENDKEY', 'SCT_FAKE_KEY_FOR_TESTS', {'code': 500}),
                 (pushplus.push_pushplus, 'PUSHPLUS_TOKEN', 'FAKE_PUSHPLUS_TOKEN', {'code': 400}),
                 (qmsg.push_qmsg, 'QMSG_TOKEN', 'FAKE_QMSG_TOKEN', {'success': False})]
        for function, name, value, data in cases:
            with self.subTest(name=name), patch.dict(os.environ, {name: value}), \
                 patch.object(http_client, 'post', return_value=response(data)):
                self.assertFalse(function(['offline']))

    def test_pushplus_keeps_key_out_of_url(self):
        with patch.dict(os.environ, {'PUSHPLUS_TOKEN': 'FAKE_PUSHPLUS_TOKEN'}), \
             patch.object(http_client, 'post', return_value=response({'code': 200})) as post:
            self.assertTrue(pushplus.push_pushplus(['offline']))
        self.assertEqual(post.call_args.args[0], 'https://www.pushplus.plus/send')
        self.assertEqual(post.call_args.kwargs['json']['token'], 'FAKE_PUSHPLUS_TOKEN')

    def test_push_failure_does_not_skip_other_channels(self):
        first, second = Mock(side_effect=RuntimeError('offline')), Mock(return_value=True)
        with patch.object(push, 'PUSHERS', {'first': first, 'second': second}):
            self.assertFalse(push.push(['offline']))
        second.assert_called_once()

    def test_config_environment_precedence_and_old_typo(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder, 'config.ini')
            file.write_text('[PUSH_CONFIG]\nSC3_SENDKEY=SCT_FILE_KEY\nPUSHPLUSH_TOKEN=FILE_PUSHPLUS_KEY\nTOKEN=SHOULD_NOT_LOAD\n', encoding='utf-8')
            with patch.dict(os.environ, {'SKYLAND_PUSH_CONFIG': str(file), 'SC3_SENDKEY': 'SCT_ENV_KEY'}):
                push.load_config_to_env()
                self.assertEqual(os.environ['SC3_SENDKEY'], 'SCT_ENV_KEY')
                self.assertEqual(os.environ['PUSHPLUS_TOKEN'], 'FILE_PUSHPLUS_KEY')
                self.assertNotIn('TOKEN', os.environ)

    def test_log_filter_redacts_exception_and_message(self):
        key = register_secret('FAKE_SECRET_FOR_REDACTION')
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.addFilter(RedactingFilter())
        logger = logging.Logger('redaction-test')
        logger.addHandler(handler)
        try:
            raise RuntimeError('https://example.invalid/' + key)
        except RuntimeError:
            logger.error('request contained %s', key, exc_info=True)
        self.assertNotIn(key, stream.getvalue())
        self.assertIn('*****', stream.getvalue())

    def test_failed_device_initialization_still_notifies(self):
        with patch.dict(os.environ, {'TOKEN': 'FAKE_ACCOUNT_ONE'}), \
             patch.object(skyland, 'get_d_id', side_effect=RuntimeError('device unavailable')), \
             patch.object(push, 'push', return_value=True) as notify:
            result = main.run(interactive=False, log_to_file=False)
        self.assertFalse(result['success'])
        self.assertIn('device unavailable', notify.call_args.args[0][0])

    def test_exit_policy_defaults_to_sign_failure_and_can_include_push(self):
        self.assertEqual(main.exit_code({'success': False, 'push_success': True}), 1)
        os.environ['EXIT_WHEN_FAIL'] = 'off'
        self.assertEqual(main.exit_code({'success': False, 'push_success': True}), 0)
        os.environ['EXIT_WHEN_PUSH_FAIL'] = 'on'
        self.assertEqual(main.exit_code({'success': True, 'push_success': False}), 1)

    def test_cloud_uses_runtime_root_instead_of_current_directory(self):
        with patch.dict(os.environ, {'RUNTIME_CODE_ROOT': '/example/cloud-code'}):
            self.assertEqual(index.default_token_path(), Path('/example/cloud-code/INPUT_HYPERGRYPH_TOKEN.txt'))

    def test_cloud_run_uses_shared_noninteractive_entry_and_restores_env(self):
        with patch.object(index, 'run', return_value={'success': True, 'push_success': True, 'logs': []}) as run:
            index.run_cloud()
            run.assert_called_once_with(interactive=False, log_to_file=False)
        self.assertNotIn('TOKEN_FILE', os.environ)

    def test_cloud_failure_is_json_and_nonzero_exit(self):
        result = {'success': False, 'push_success': True, 'logs': ['offline failure']}
        stream = io.StringIO()
        with patch.object(index, 'run_cloud', return_value=result), contextlib.redirect_stdout(stream):
            self.assertEqual(index.main(), 1)
        self.assertEqual(json.loads(stream.getvalue())['errorType'], 'SignInFailed')
        with patch.object(index, 'run_cloud', return_value=result):
            with self.assertRaises(RuntimeError):
                index.handler({}, None)

    def test_local_entry_fails_without_accounts_instead_of_prompting(self):
        env = dict(os.environ, TOKEN='', PYTHONIOENCODING='utf-8')
        with tempfile.TemporaryDirectory() as folder:
            completed = subprocess.run([sys.executable, str(ROOT / 'src' / 'main.py')],
                                       cwd=folder, env=env, capture_output=True, timeout=20)
        self.assertEqual(completed.returncode, 1)

    def test_source_docker_configuration_excludes_credentials(self):
        dockerfile = (ROOT / 'Dockerfile').read_text(encoding='utf-8')
        ignored = (ROOT / '.dockerignore').read_text(encoding='utf-8')
        self.assertNotIn('COPY . .', dockerfile)
        for pattern in ('**/TOKEN.txt', '**/INPUT_HYPERGRYPH_TOKEN.txt', '**/config.ini'):
            self.assertIn(pattern, ignored)
        self.assertTrue((ROOT / 'cloud_functions' / 'bootstrap').exists())


if __name__ == '__main__':
    unittest.main()
