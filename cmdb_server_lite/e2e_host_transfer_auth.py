# -*- coding: utf-8 -*-
"""主机转移 per-biz 授权 e2e：业务作用域从目标模块（cc_ModuleBase）反推。

验证点（对齐上游 host transfer 的 Parents=[business]）：
  A. tom 仅获 hostInstance transfer --biz-id 2：
       · 转移到 biz2 模块(4) 过网关(code 0)
       · 转移到 biz1 模块(1) 被拒(1302102)，且权限体 business_id='1'
       · 权限体 business_id='2'（解析器从 module_id=4 反推出 biz2）
  B. 追加 class-level（全业务）hostInstance transfer：
       · 转移到 biz1 模块(1) 过网关（类级是全部业务的超集）
  C. 撤销全部 hostInstance transfer：
       · 转移到 biz2 模块(4) 被拒(1302102)（tom 已无任何转移策略）
  清理：删除测试主机的 cc_ModuleHostConfig 绑定；撤销 tom 的 hostInstance 策略。
"""
import sys, os, subprocess, json, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
SRV = os.path.join(HERE, 'bk-cmdb-lite', 'cmdb_server_lite')
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(SRV, '.env'))
except Exception:
    pass
sys.path.insert(0, SRV)
os.chdir(SRV)

BASE = 'http://localhost:5000'
PASS = 0
FAIL = 0
TEST_HOSTS = [90001, 90002, 90003]  # 仅用于 cc_ModuleHostConfig 绑定，便于清理


def check(name, ok, detail=''):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f'  ✅ {name}  {detail}')
    else:
        FAIL += 1
        print(f'  ❌ {name}  {detail}')


def run_cli(*args, expect_rc=0):
    env = dict(os.environ)
    cmd = [sys.executable, '-m', 'app.cli.cmdb', 'auth', *args]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=SRV)
    return p.returncode, p.stdout, p.stderr


def code_of(r):
    if not isinstance(r, dict):
        return None
    if r.get('result') is True or r.get('code') == 0:
        return 0
    return r.get('bk_error_code')


def call(method, path, token, json_body=None, params=None):
    import requests
    h = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    fn = getattr(requests, method.lower())
    r = fn(BASE + path, headers=h, json=json_body, params=params, timeout=20)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}


def make_token(payload):
    from app.auth.token import make_token
    return make_token(payload)


def biz_of_denied(body):
    """从 1302102 权限体里取 business_id（证明解析器挂上了业务作用域）。

    拒绝响应结构：body['permission']['permissions'][0]['business_id']
    （顶层是单数 permission，内层才是 permissions 列表）。
    """
    perm = (body or {}).get('permission') or {}
    perms = perm.get('permissions') or []
    if not perms:
        return None
    return perms[0].get('business_id')


def cleanup_host_bindings():
    con = sqlite3.connect('cmdb_dev.db')
    con.execute('DELETE FROM cc_ModuleHostConfig WHERE bk_host_id IN (%s)'
                % ','.join(str(h) for h in TEST_HOSTS))
    con.commit()
    con.close()


# ---------------------------------------------------------------------------
print('\n===== 准备：确保 tom 存在 + 清场 =====')
admin = make_token({'bk_user_name': 'admin', 'bk_supplier_account': '0', 'bk_role': 1})
tom = make_token({'bk_user_name': 'tom', 'bk_supplier_account': '0', 'bk_role': 2})

# tom 若不存在则创建（CLI grant 要求用户存在）
rc, out, err = run_cli('user', 'create', '--name', 'tom', '--password', 'tom123456', '--role', '2')
print(f'  (tom create rc={rc}, 已存在则忽略)')
cleanup_host_bindings()
# 清掉 tom 既有 hostInstance 策略，保证从零开始
run_cli('policy', 'revoke', '--user', 'tom', '--res-type', 'hostInstance', '--action', 'transfer')

con = sqlite3.connect('cmdb_dev.db'); con.row_factory = sqlite3.Row
n0 = con.execute("SELECT count(*) n FROM cc_AuthPolicy WHERE principal='tom' AND res_type='hostInstance'").fetchone()['n']
con.close()
check('tom 初始无 hostInstance 策略', n0 == 0, f'n0={n0}')

# ---------------------------------------------------------------------------
print('\n===== A. tom 仅获 hostInstance transfer --biz-id 2 =====')
rc, out, err = run_cli('policy', 'grant', '--user', 'tom', '--res-type', 'hostInstance',
                       '--action', 'transfer', '--biz-id', '2')
check('A grant --biz-id 2 退出0', rc == 0, f'rc={rc} {err[-120:]}')
con = sqlite3.connect('cmdb_dev.db'); con.row_factory = sqlite3.Row
rows = con.execute("SELECT * FROM cc_AuthPolicy WHERE principal='tom' AND res_type='hostInstance'").fetchall()
con.close()
check('A 落库 1 行 business_id=2', len(rows) == 1 and rows[0]['business_id'] == '2',
      f'rows={[(r["action"], r["business_id"]) for r in rows]}')

# A1: 转移到 biz2 普通模块(100, default=0) 应成功
st, r = call('POST', '/api/v1/host/transfer/modules', tom,
             json_body={'bk_biz_id': 2, 'bk_host_id': [90001], 'module_id': [100], 'transfer_type': 'business'})
check('A1 转移到 biz2 模块(100) 过网关', code_of(r) == 0, f'code={code_of(r)} body={r}')

# A2: 转移到 biz1 空闲模块(1, default=1) 应被拒 1302102，且权限体 business_id='1'
st, r = call('POST', '/api/v1/host/transfer/modules', tom,
             json_body={'bk_biz_id': 1, 'bk_host_id': [90002], 'module_id': [1], 'transfer_type': 'idle'})
check('A2 转移到 biz1 模块(1) 被拒 1302102', code_of(r) == 1302102, f'code={code_of(r)} body={r}')
check('A2 权限体 business_id="1"（解析器从 module 1 反推 biz1）', biz_of_denied(r) == '1',
      f'biz={biz_of_denied(r)}')

# ---------------------------------------------------------------------------
print('\n===== B. 追加 class-level（全业务）hostInstance transfer =====')
rc, out, err = run_cli('policy', 'grant', '--user', 'tom', '--res-type', 'hostInstance', '--action', 'transfer')
check('B grant 全业务 退出0', rc == 0, f'rc={rc}')
con = sqlite3.connect('cmdb_dev.db'); con.row_factory = sqlite3.Row
rows = con.execute("SELECT business_id FROM cc_AuthPolicy WHERE principal='tom' AND res_type='hostInstance'").fetchall()
con.close()
bizs = sorted([(r['business_id'] or 'NULL') for r in rows])
check('B 现有 2 行 [2, NULL]', bizs == ['2', 'NULL'], f'bizs={bizs}')

# B1: 类级覆盖全部业务 → 转移到 biz1 空闲模块(1) 现在成功
st, r = call('POST', '/api/v1/host/transfer/modules', tom,
             json_body={'bk_biz_id': 1, 'bk_host_id': [90002], 'module_id': [1], 'transfer_type': 'idle'})
check('B1 类级下转移到 biz1 模块(1) 过网关', code_of(r) == 0, f'code={code_of(r)} body={r}')

# ---------------------------------------------------------------------------
print('\n===== C. 撤销全部 hostInstance transfer =====')
rc, out, err = run_cli('policy', 'revoke', '--user', 'tom', '--res-type', 'hostInstance', '--action', 'transfer')
check('C revoke 退出0', rc == 0, f'rc={rc}')
con = sqlite3.connect('cmdb_dev.db'); con.row_factory = sqlite3.Row
n1 = con.execute("SELECT count(*) n FROM cc_AuthPolicy WHERE principal='tom' AND res_type='hostInstance'").fetchone()['n']
con.close()
check('C tom hostInstance 策略清零', n1 == 0, f'n1={n1}')

# C1: 无策略 → 转移到 biz2 普通模块(100) 被拒 1302102，权限体 business_id='2'
st, r = call('POST', '/api/v1/host/transfer/modules', tom,
             json_body={'bk_biz_id': 2, 'bk_host_id': [90003], 'module_id': [100], 'transfer_type': 'business'})
check('C1 无策略转移到 biz2 模块(100) 被拒 1302102', code_of(r) == 1302102, f'code={code_of(r)}')
check('C1 权限体 business_id="2"（解析器从 module 100 反推 biz2）', biz_of_denied(r) == '2',
      f'biz={biz_of_denied(r)}')

# ---------------------------------------------------------------------------
print('\n===== 清理 =====')
cleanup_host_bindings()
run_cli('policy', 'revoke', '--user', 'tom', '--res-type', 'hostInstance', '--action', 'transfer')
print(f'\n===== RESULT: PASS={PASS} FAIL={FAIL} =====')
sys.exit(1 if FAIL else 0)
