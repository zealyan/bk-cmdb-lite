# -*- coding: utf-8 -*-
"""跨业务主机转移 e2e（API 层 + DB 校验）。

对齐原项目 POST /hosts/modules/across/biz（TransferHostAcrossBusiness）。
源业务 A=2（蓝鲸平台），目标业务 B=3（正式环境）。
测试主机 90001/90002/90003 仅作 cc_HostBase + cc_ModuleHostConfig 绑定，便于清理。

覆盖用例：
  T1 未登录 → 1302102（门禁先于业务逻辑）
  T2 缺 src_bk_biz_id → 1101000（CCErrCommParamsInvalid）
  T3 源业务 == 目标业务 → 1101000
  T4 目标模块不属于目标业务 → 1101000
  T5 admin 成功转移（单主机 90001: 业务2/模块100 -> 业务3/模块200），DB 绑定迁移校验
  T6 tom 仅获源业务权限：跨到业务3 → 1302102，且权限体含 business_id='3'（双业务维度）
  T7 admin 多主机多模块成功转移（90002/90003: 业务2 -> 业务4/模块300）
"""
import sys, os, subprocess, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, '.env'))
except Exception:
    pass
sys.path.insert(0, HERE)
os.chdir(HERE)

BASE = 'http://localhost:5000'
PASS = 0
FAIL = 0
TEST_HOSTS = [90001, 90002, 90003]
SRC_BIZ = 2   # 蓝鲸平台
DST_BIZ = 3   # 正式环境
DST_BIZ4 = 4  # 测试环境


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
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=HERE)
    return p.returncode, p.stdout, p.stderr


def fresh_token(payload):
    """每次调用现签 token（CMDB_TOKEN_MAX_AGE=30，随用随签避免过期）"""
    from app.auth.token import make_token
    return make_token(payload)


def call(method, path, token=None, json_body=None, params=None):
    import requests
    h = {'Content-Type': 'application/json'}
    if token:
        # 部署形态：supervisor 注入 CMDB_AUTH_PAYLOAD_ORDER=COOKIE,X_LITE_TOKEN，
        # Bearer 通道关闭（agentos 网关会污染 Authorization），走 X-Lite-Token。
        h['X-Lite-Token'] = token
    fn = getattr(requests, method.lower())
    r = fn(BASE + path, headers=h, json=json_body, params=params, timeout=20)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}


def code_of(r):
    if not isinstance(r, dict):
        return None
    if r.get('result') is True or r.get('code') == 0:
        return 0
    return r.get('bk_error_code')


def denied_biz_ids(body):
    """1302102 权限体里的 business_id 集合（双业务维度验证）。"""
    perm = (body or {}).get('permission') or {}
    perms = perm.get('permissions') or []
    return {str(p.get('business_id')) for p in perms if p.get('business_id') is not None}


# ---------------------------------------------------------------------------
def db_row(sql, params=()):
    con = sqlite3.connect('cmdb_dev.db')
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def bindings_of(host_id):
    return db_row(
        'SELECT bk_biz_id, bk_module_id, bk_set_id FROM cc_ModuleHostConfig '
        'WHERE bk_host_id=? ORDER BY bk_biz_id, bk_module_id', (host_id,))


def prepare_data():
    con = sqlite3.connect('cmdb_dev.db')
    cur = con.cursor()
    now = '2026-08-16 21:40:00'
    for i, h in enumerate(TEST_HOSTS, 1):
        cur.execute(
            'INSERT OR IGNORE INTO cc_HostBase '
            '(_id, bk_host_id, bk_host_name, bk_host_innerip, bk_cloud_id, bk_supplier_account, '
            ' create_time, last_time, creator, modifier) '
            'VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?)',
            (f'host_{h}', h, f'e2e-across-host-0{i}', f'192.168.90.{i}', '0', now, now, 'e2e', 'e2e'))
    # 源绑定：业务2
    cur.execute('DELETE FROM cc_ModuleHostConfig WHERE bk_host_id IN (%s)'
                % ','.join(str(x) for x in TEST_HOSTS))
    cur.executemany(
        'INSERT INTO cc_ModuleHostConfig (bk_biz_id, bk_host_id, bk_module_id, bk_set_id, bk_supplier_account) '
        'VALUES (?, ?, ?, ?, ?)',
        [(SRC_BIZ, 90001, 100, 10, '0'),
         (SRC_BIZ, 90002, 100, 10, '0'),
         (SRC_BIZ, 90003, 101, 10, '0')])
    con.commit()
    con.close()


def cleanup():
    con = sqlite3.connect('cmdb_dev.db')
    cur = con.cursor()
    cur.execute('DELETE FROM cc_ModuleHostConfig WHERE bk_host_id IN (%s)'
                % ','.join(str(x) for x in TEST_HOSTS))
    cur.execute('DELETE FROM cc_HostBase WHERE bk_host_id IN (%s)'
                % ','.join(str(x) for x in TEST_HOSTS))
    con.commit()
    con.close()
    run_cli('policy', 'revoke', '--user', 'tom', '--res-type', 'hostInstance', '--action', 'transfer')


# ---------------------------------------------------------------------------
print('\n===== 准备 =====')
run_cli('user', 'create', '--name', 'tom', '--password', 'tom123456', '--role', '2')
prepare_data()
run_cli('policy', 'revoke', '--user', 'tom', '--res-type', 'hostInstance', '--action', 'transfer')
print('  测试主机绑定:', bindings_of(90001))

# T1 未登录门禁
print('\n===== T1 未登录 → 1302102 =====')
st, r = call('POST', '/api/v1/host/transfer/modules/across/biz',
             json_body={'src_bk_biz_id': SRC_BIZ, 'dst_bk_biz_id': DST_BIZ,
                        'bk_host_id': [90001], 'module_id': [200]})
check('T1 未登录被拒 1302102', code_of(r) == 1302102, f'code={code_of(r)} body={r}')

# T2 缺参数
print('\n===== T2 缺 src_bk_biz_id → 1101000 =====')
st, r = call('POST', '/api/v1/host/transfer/modules/across/biz',
             token=fresh_token({'bk_user_name': 'admin', 'bk_supplier_account': '0', 'bk_role': 1}),
             json_body={'dst_bk_biz_id': DST_BIZ, 'bk_host_id': [90001], 'module_id': [200]})
check('T2 缺源业务ID → 1199006', code_of(r) == 1199006, f'code={code_of(r)}')

# T3 源=目标
print('\n===== T3 源业务==目标业务 → 1101000 =====')
st, r = call('POST', '/api/v1/host/transfer/modules/across/biz',
             token=fresh_token({'bk_user_name': 'admin', 'bk_supplier_account': '0', 'bk_role': 1}),
             json_body={'src_bk_biz_id': DST_BIZ, 'dst_bk_biz_id': DST_BIZ,
                        'bk_host_id': [90001], 'module_id': [200]})
check('T3 源=目标被拒 1199006', code_of(r) == 1199006, f'code={code_of(r)}')

# T4 目标模块不属于目标业务（模块1 属于业务1）
print('\n===== T4 目标模块不属于目标业务 → 1101000 =====')
st, r = call('POST', '/api/v1/host/transfer/modules/across/biz',
             token=fresh_token({'bk_user_name': 'admin', 'bk_supplier_account': '0', 'bk_role': 1}),
             json_body={'src_bk_biz_id': SRC_BIZ, 'dst_bk_biz_id': DST_BIZ,
                        'bk_host_id': [90001], 'module_id': [1]})
check('T4 跨业务模块混用被拒 1199006', code_of(r) == 1199006, f'code={code_of(r)}')

# T5 admin 成功转移单主机
print('\n===== T5 admin 成功转移 90001: 业务2/模块100 -> 业务3/模块200 =====')
st, r = call('POST', '/api/v1/host/transfer/modules/across/biz',
             token=fresh_token({'bk_user_name': 'admin', 'bk_supplier_account': '0', 'bk_role': 1}),
             json_body={'src_bk_biz_id': SRC_BIZ, 'dst_bk_biz_id': DST_BIZ,
                        'bk_host_id': [90001], 'module_id': [200]})
check('T5 接口成功 code=0', code_of(r) == 0, f'code={code_of(r)} body={r}')
b = bindings_of(90001)
check('T5 源业务绑定已清除（无 biz2）', not any(x[0] == SRC_BIZ for x in b), f'bindings={b}')
check('T5 目标业务绑定新增 (3,200,20)', (3, 200, 20) in b, f'bindings={b}')

# T6 tom 仅源业务权限 → 跨业务应被拒（双业务维度）
print('\n===== T6 tom 仅获业务2 transfer 权限，跨到业务3 → 1302102 =====')
rc, out, err = run_cli('policy', 'grant', '--user', 'tom', '--res-type', 'hostInstance',
                       '--action', 'transfer', '--biz-id', '2')
check('T6 grant tom biz2 transfer 退出0', rc == 0, f'rc={rc} {err[-120:]}')
st, r = call('POST', '/api/v1/host/transfer/modules/across/biz',
             token=fresh_token({'bk_user_name': 'tom', 'bk_supplier_account': '0', 'bk_role': 2}),
             json_body={'src_bk_biz_id': SRC_BIZ, 'dst_bk_biz_id': DST_BIZ,
                        'bk_host_id': [90002], 'module_id': [200]})
check('T6 tom 跨业务被拒 1302102', code_of(r) == 1302102, f'code={code_of(r)} body={r}')
biz_ids = denied_biz_ids(r)
check('T6 权限体含目标业务 business_id="3"（双维度）', '3' in biz_ids, f'biz_ids={biz_ids}')

# T6b tom 追加全业务权限后应成功（类级是全部业务超集）
print('\n===== T6b tom 追加 class-level transfer → 跨业务成功 =====')
rc, out, err = run_cli('policy', 'grant', '--user', 'tom', '--res-type', 'hostInstance',
                       '--action', 'transfer')
check('T6b grant 全业务 退出0', rc == 0, f'rc={rc}')
st, r = call('POST', '/api/v1/host/transfer/modules/across/biz',
             token=fresh_token({'bk_user_name': 'tom', 'bk_supplier_account': '0', 'bk_role': 2}),
             json_body={'src_bk_biz_id': SRC_BIZ, 'dst_bk_biz_id': DST_BIZ,
                        'bk_host_id': [90002], 'module_id': [200]})
check('T6b tom 类级权限下跨业务成功', code_of(r) == 0, f'code={code_of(r)} body={r}')

# T7 admin 多主机（90003 业务2/模块101 -> 业务4/模块300）
print('\n===== T7 admin 多主机转移 90003: 业务2/模块101 -> 业务4/模块300 =====')
st, r = call('POST', '/api/v1/host/transfer/modules/across/biz',
             token=fresh_token({'bk_user_name': 'admin', 'bk_supplier_account': '0', 'bk_role': 1}),
             json_body={'src_bk_biz_id': SRC_BIZ, 'dst_bk_biz_id': DST_BIZ4,
                        'bk_host_id': [90003], 'module_id': [300]})
check('T7 多主机接口成功 code=0', code_of(r) == 0, f'code={code_of(r)} body={r}')
b3 = bindings_of(90003)
check('T7 90003 源绑定清除 + 目标 (4,300,30) 新增',
      not any(x[0] == SRC_BIZ for x in b3) and (4, 300, 30) in b3, f'bindings={b3}')

# ---------------------------------------------------------------------------
print('\n===== 清理 =====')
cleanup()
print(f'\n===== RESULT: PASS={PASS} FAIL={FAIL} =====')
sys.exit(1 if FAIL else 0)
