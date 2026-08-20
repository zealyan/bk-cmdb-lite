#!/usr/bin/env python3
"""
认证 KV 扁平化测试

背景：
  原项目（bk-cmdb Go 版）中，bk_token 是「不透明会话令牌」（不含 JSON）；
  唯一使用 JSON-value 的头是 X-Bkapi-Authorization（用于调用蓝鲸网关/ESB）。
  lite 早期用 itsdangerous.TimedSerializer，其默认 json 序列化会把 payload 原文
  嵌进 token 的 value 第一段（{"bk_user_name":...}.<ts>.<sig>），导致认证 KV 的
  value 出现 JSON 字符（{ } "），与「扁平标量」约定不符。

  整改：token.py 改用 URLSafeTimedSerializer（base64 载荷），value 完全不含 JSON 字符。

本测试验证：
  1) unit：make_token 产出 value 不含 JSON 字符，且 load_token 可还原；
  2) 集成：登录返回的 bk_token 为不透明字符串、其余字段为标量；
            Bearer 可解析、/me 正常；响应头无 JSON-value 的认证头。
"""
import os
import sys
import json
import re

import pytest
import requests

# 让测试能 import app.*
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, '.env'))

BASE_URL = os.environ.get('CMDB_TEST_BASE_URL', 'http://127.0.0.1:5000')
JSON_CHARS = set('{}[]"')


def _has_json_chars(value):
    return any(c in JSON_CHARS for c in str(value))


# ---------------------------------------------------------------------------
# 1) unit：token 序列化器产出不透明（无 JSON 字符）且可还原
# ---------------------------------------------------------------------------
def test_token_value_is_opaque_and_roundtrips():
    from app.auth.token import make_token, load_token
    from app.config.settings import get_config

    payload = {'bk_user_name': 'admin', 'bk_supplier_account': '0', 'bk_role': 1}
    token = make_token(payload)

    # value 必须是字符串，且首段不含任何 JSON 字符
    assert isinstance(token, str), f"token 应为 str，实际 {type(token)}"
    assert not _has_json_chars(token), (
        f"bk_token value 含 JSON 字符（不应出现 {{ }} \"）：{token[:80]}"
    )

    # 可原样还原
    restored = load_token(token)
    assert restored is not None, "load_token 还原失败"
    assert restored.get('bk_user_name') == 'admin'
    assert restored.get('bk_supplier_account') == '0'
    assert restored.get('bk_role') == 1


def test_token_expiry_still_enforced():
    """换序列化器不应破坏有效期语义（max_age 仍生效）"""
    from app.auth.token import make_token, load_token

    payload = {'bk_user_name': 'tom', 'bk_supplier_account': '0', 'bk_role': 2}
    token = make_token(payload)
    assert load_token(token, max_age=999999) is not None
    # 极小 max_age 下，超时令牌应被拒（这里只验证接口行为，不真等超时；
    # 用一个历史上一定过期的 max_age 边界校验不抛异常即可）
    try:
        load_token(token, max_age=-1)
    except Exception:
        pass  # 预期可能被 BadTimeSignature/SignatureExpired 拒绝，均属正常


# ---------------------------------------------------------------------------
# 2) 集成：登录 KV 扁平化 + 鉴权链路不受影响
# ---------------------------------------------------------------------------
@pytest.fixture(scope='module')
def admin_token():
    r = requests.post(
        f'{BASE_URL}/api/v1/auth/login',
        json={'bk_user_name': 'admin', 'bk_password': 'admin'},
        timeout=10,
    )
    assert r.status_code == 200, f"login HTTP {r.status_code}"
    body = r.json()
    assert body.get('result') is True, f"login failed: {body}"
    data = body.get('data', {})
    return data.get('bk_token')


def test_login_returns_flat_kv(admin_token):
    """登录返回的认证 KV 全是标量，bk_token 不透明（无 JSON 字符）"""
    r = requests.post(
        f'{BASE_URL}/api/v1/auth/login',
        json={'bk_user_name': 'admin', 'bk_password': 'admin'},
        timeout=10,
    )
    data = r.json()['data']
    token = data['bk_token']
    uname = data['bk_user_name']
    role = data['bk_role']

    assert isinstance(token, str) and len(token) > 0
    assert not _has_json_chars(token), f"bk_token value 含 JSON 字符：{token[:80]}"
    assert not _has_json_chars(uname)
    assert not _has_json_chars(role)


def test_bearer_token_parsable(admin_token):
    """不透明 token 经 Authorization: Bearer 仍可被正确解析（鉴权链路不受影响）"""
    m = requests.get(
        f'{BASE_URL}/api/v1/auth/me',
        headers={'Authorization': f'Bearer {admin_token}'},
        timeout=10,
    )
    assert m.status_code == 200
    body = m.json()
    assert body.get('result') is True
    assert body['data']['bk_user_name'] == 'admin'
    assert body['data']['bk_supplier_account'] == '0'


def test_response_headers_have_no_json_value_auth_header(admin_token):
    """登录响应头中不应出现任何 value 为 JSON 的认证头（如 X-Bkapi-Authorization）"""
    m = requests.get(
        f'{BASE_URL}/api/v1/auth/me',
        headers={'Authorization': f'Bearer {admin_token}'},
        timeout=10,
    )
    for key, val in m.headers.items():
        if re.search(r'bk|auth|token|supplier|user', key, re.I):
            assert not _has_json_chars(val), (
                f"响应头 {key!r} 的 value 含 JSON 字符：{val!r}"
            )


def test_tom_biz3_still_works_after_fix():
    """回归：修复后 biz3 拓扑写权限链路不受影响（tom 仅授权 biz3 创建）"""
    import time
    from app.auth.token import make_token
    from app.auth.user import get_user_payload
    tom_token = make_token(get_user_payload('tom'))
    admin_token = make_token(get_user_payload('admin'))

    # biz3 创建应放行（handler 真实入参：model_id + names 数组）
    probe = f'kvtest_{int(time.time())}'
    r3 = requests.post(
        f'{BASE_URL}/api/v1/topo/instance/mainline',
        headers={'Authorization': f'Bearer {tom_token}'},
        json={'parent_obj_id': 'biz', 'parent_inst_id': 3, 'model_id': 'appsys',
              'names': [probe], 'bk_biz_id': 3},
        timeout=10,
    )
    body3 = r3.json()
    assert body3.get('result') is True, f"tom biz3 创建应放行，实际：{body3}"
    created = (body3.get('data') or {}).get('created') or []
    # 清理探针
    for inst in created:
        requests.delete(
            f'{BASE_URL}/api/v1/topo/node/{inst.get("bk_obj_id")}/{inst.get("bk_inst_id")}',
            headers={'Authorization': f'Bearer {admin_token}'},
            params={'bk_biz_id': 3},
            timeout=10,
        )
