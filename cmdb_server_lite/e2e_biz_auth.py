# -*- coding: utf-8 -*-
"""per-biz 授权 e2e：对齐上游 business_id 独立列。

Part A（临时副本库，无锁/无污染）：CLI 落库正确性
  - grant --biz-id 2 topo-admin → 3 行 business_id='2'
  - grant 同名不传 --biz-id → 3 行 business_id=NULL（与 biz2 互不重复，幂等按 (biz) 区分）
  - grant-scenario topo-admin --biz-id 3 → 3 行 business_id='3'
  - list --biz-id 2 / 不传 的过滤行为
  - revoke --biz-id 2 仅删 biz2，保留 NULL 与 biz3
  - 非法 res_type/action 退出码 2

Part B（真实网关，cmdb_dev.db）：per-biz 隔离端到端
  - tom 仅授 topo-admin --biz-id 2：
      · 创建集群 biz2 过网关；创建集群 biz1 被拒 1302102
      · 创建模块（set 10, biz2）过网关；编辑节点 set 2(biz2) 过网关；删除节点 module 4(biz2) 过网关
      · 编辑节点 set 1(biz1) 被拒 1302102；删除节点 module 1(biz1) 被拒 1302102
  - 改为 grant topo-admin（全业务）→ 上述 biz1 操作全部过网关
  - 撤销全业务 → 还原
  - 清理：删除测试创建的集群/模块，host 还原
"""
import sys, os, subprocess, json, copy, shutil, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
SRV = os.path.join(HERE, 'bk-cmdb-lite', 'cmdb_server_lite')
# 必须在导入 app / 调用 make_token 之前加载 .env，
# 否则 make_token 用代码默认 SECRET_KEY 签名，与实时后端(.env 密钥)不一致 → load_token 失败 → 直接 1302102。
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


def check(name, ok, detail=''):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f'  ✅ {name}  {detail}')
    else:
        FAIL += 1
        print(f'  ❌ {name}  {detail}')


def run_cli(*args, db=None, expect_rc=0):
    env = dict(os.environ)
    cmd = [sys.executable, '-m', 'app.cli.cmdb', 'auth', *args]
    if db:
        cmd += ['--db', db]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=SRV)
    return p.returncode, p.stdout, p.stderr


def code_of(r):
    # 成功响应用 code:0 + result:true（无 bk_error_code）；错误响应用 bk_error_code。
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


# ---------------------------------------------------------------------------
print('\n===== Part A: CLI 落库正确性（临时副本库） =====')
TMP = '/tmp/biz_auth_test.db'
if os.path.exists(TMP):
    os.remove(TMP)
shutil.copyfile('cmdb_dev.db', TMP)

# A1: grant --biz-id 2 topo-admin → 3 行 business_id='2'
rc, out, err = run_cli('policy', 'grant-scenario', '--user', 'tom',
                       '--scenario', 'topo-admin', '--biz-id', '2', db=TMP)
check('A1 grant-scenario topo-admin --biz-id 2 退出0', rc == 0, f'rc={rc} err={err[-120:]}')
con = sqlite3.connect(TMP); con.row_factory = sqlite3.Row
biz2 = con.execute("SELECT count(*) n FROM cc_AuthPolicy WHERE principal='tom' AND res_type='biz_topology' AND business_id='2'").fetchone()['n']
check('A1 落库 3 行 business_id=2', biz2 == 3, f'got {biz2}')
con.close()

# A2: 同名不传 --biz-id（全业务）→ 3 行 business_id=NULL，且与 biz2 不重复
rc, out, err = run_cli('policy', 'grant-scenario', '--user', 'tom',
                       '--scenario', 'topo-admin', db=TMP)
check('A2 grant-scenario topo-admin(全业务) 退出0', rc == 0, f'rc={rc}')
con = sqlite3.connect(TMP); con.row_factory = sqlite3.Row
nullbiz = con.execute("SELECT count(*) n FROM cc_AuthPolicy WHERE principal='tom' AND res_type='biz_topology' AND business_id IS NULL").fetchone()['n']
check('A2 落库 3 行 business_id=NULL（与 biz2 独立）', nullbiz == 3, f'got {nullbiz}')
# 幂等：再 grant 一次 biz2 不应新增
rc, out, err = run_cli('policy', 'grant-scenario', '--user', 'tom',
                       '--scenario', 'topo-admin', '--biz-id', '2', db=TMP)
con = sqlite3.connect(TMP); con.row_factory = sqlite3.Row
biz2b = con.execute("SELECT count(*) n FROM cc_AuthPolicy WHERE principal='tom' AND res_type='biz_topology' AND business_id='2'").fetchone()['n']
check('A2 幂等：biz2 仍为 3 行（未重复）', biz2b == 3, f'got {biz2b}')
con.close()

# A3: grant-scenario topo-admin --biz-id 3 → 3 行 business_id='3'
rc, out, err = run_cli('policy', 'grant-scenario', '--user', 'tom',
                       '--scenario', 'topo-admin', '--biz-id', '3', db=TMP)
con = sqlite3.connect(TMP); con.row_factory = sqlite3.Row
biz3 = con.execute("SELECT count(*) n FROM cc_AuthPolicy WHERE principal='tom' AND res_type='biz_topology' AND business_id='3'").fetchone()['n']
check('A3 落库 3 行 business_id=3', biz3 == 3, f'got {biz3}')
# list --biz-id 2 仅返回 biz2 + NULL（类级继承）；用 --json 取单行 JSON
rc, out, err = run_cli('policy', 'list', '--user', 'tom', '--biz-id', '2', '--json', db=TMP)
lst = json.loads(out).get('policies', [])
# 仅统计 biz_topology（排除预存 modelInstance 基类级行对计数的干扰）
bt = [r for r in lst if r.get('res_type') == 'biz_topology']
check('A3 list --biz-id 2 返回 biz2+NULL(类级继承, 仅 biz_topology)',
      all((r.get('business_id') in ('2', None)) for r in bt)
      and len(bt) == 6, f'count={len(bt)}')
con.close()

# A4: revoke --biz-id 2 仅删 biz2，保留 NULL 与 biz3
rc, out, err = run_cli('policy', 'revoke', '--user', 'tom', '--res-type', 'biz_topology',
                       '--action', 'create,update,delete', '--biz-id', '2', db=TMP)
con = sqlite3.connect(TMP); con.row_factory = sqlite3.Row
biz2c = con.execute("SELECT count(*) n FROM cc_AuthPolicy WHERE principal='tom' AND business_id='2'").fetchone()['n']
nullc = con.execute("SELECT count(*) n FROM cc_AuthPolicy WHERE principal='tom' AND res_type='biz_topology' AND business_id IS NULL").fetchone()['n']
biz3c = con.execute("SELECT count(*) n FROM cc_AuthPolicy WHERE principal='tom' AND business_id='3'").fetchone()['n']
con.close()
check('A4 revoke --biz-id 2 仅删 biz2', biz2c == 0 and nullc == 3 and biz3c == 3,
      f'biz2={biz2c} null={nullc} biz3={biz3c}')
# 清理副本
os.remove(TMP)

# A5: 非法 res_type/action 退出码 2
rc, out, err = run_cli('policy', 'grant', '--user', 'tom', '--res-type', 'NOPE',
                       '--action', 'create', db='cmdb_dev.db')
check('A5 非法 res_type 退出码2', rc == 2, f'rc={rc}')
rc, out, err = run_cli('policy', 'grant', '--user', 'tom', '--res-type', 'biz_topology',
                       '--action', 'explode', db='cmdb_dev.db')
check('A5 非法 action 退出码2', rc == 2, f'rc={rc}')


# ---------------------------------------------------------------------------
print('\n===== Part B: 真实网关 per-biz 隔离 =====')
TOM = make_token({'bk_user_name': 'tom', 'bk_supplier_account': '0', 'bk_role': 2})
ADMIN = make_token({'bk_user_name': 'admin', 'bk_supplier_account': '0', 'bk_role': 1})

# B0: 基线 - tom 无任何拓扑策略时，biz2 创建集群应被拒 1302102
sc, r = call('POST', '/api/v1/topo/biz/2/set', TOM, {'names': ['e2e_baseline']})
check('B0 基线：biz2 创建集群无策略→1302102',
      code_of(r) == 1302102, f'code={code_of(r)}')
# 清理基线可能写入的（实际应被拒未写入）

# B1: 仅授 topo-admin --biz-id 2
rc, out, err = run_cli('policy', 'grant-scenario', '--user', 'tom',
                       '--scenario', 'topo-admin', '--biz-id', '2')
check('B1 CLI grant topo-admin --biz-id 2 退出0', rc == 0, f'rc={rc} {err[-100:]}')

# B2: biz2 写操作过网关；biz1 写操作被拒
sc, r = call('POST', '/api/v1/topo/biz/2/set', TOM, {'names': ['e2e_biz2_set']})
ok2 = code_of(r) == 0
check('B2 创建集群 biz2 过网关', ok2, f'code={code_of(r)}')
set2_id = (r.get('data', {}).get('created') or [{}])[0].get('bk_set_id') if ok2 else None

sc, r = call('POST', '/api/v1/topo/biz/1/set', TOM, {'names': ['e2e_biz1_set']})
check('B2 创建集群 biz1 被拒 1302102（per-biz 隔离）',
      code_of(r) == 1302102, f'code={code_of(r)}')

sc, r = call('POST', '/api/v1/topo/set/10/module', TOM, {'names': ['e2e_biz2_mod'], 'bk_biz_id': 2})  # set10→biz2
okm = code_of(r) == 0
check('B2 创建模块(set10,biz2) 过网关', okm, f'code={code_of(r)}')
mod_id = (r.get('data', {}).get('created') or [{}])[0].get('bk_module_id') if okm else None

# 编辑/删除节点：biz2 过，biz1 拒
sc, r = call('PUT', '/api/v1/topo/node/set/2', TOM, {'bk_set_name': 'e2e_edit_ok'})  # set2→biz2
check('B2 编辑节点 set2(biz2) 过网关', code_of(r) == 0, f'code={code_of(r)}')
# 还原 set2 名称
call('PUT', '/api/v1/topo/node/set/2', ADMIN, {'bk_set_name': '空闲机池'})

sc, r = call('PUT', '/api/v1/topo/node/set/1', TOM, {'bk_set_name': 'e2e_edit_deny'})  # set1→biz1
check('B2 编辑节点 set1(biz1) 被拒 1302102', code_of(r) == 1302102, f'code={code_of(r)}')

# 删除节点：用新建的空模块测 biz2 删除（module4 真实空闲机含主机不可删→1101030，会干扰判定）
sc, r = call('POST', '/api/v1/topo/set/2/module', TOM, {'names': ['e2e_biz2_delmod'], 'bk_biz_id': 2})  # biz2 创建
del_mod_id = (r.get('data', {}).get('created') or [{}])[0].get('bk_module_id')
sc, r = call('DELETE', f'/api/v1/topo/node/module/{del_mod_id}', TOM, params={'bk_biz_id': 2})  # biz2 删除 → 过网关
check('B2 删除节点 module(biz2) 过网关', code_of(r) == 0, f'code={code_of(r)}')

sc, r = call('DELETE', '/api/v1/topo/node/module/1', TOM, params={'bk_biz_id': 1})  # module1→biz1
check('B2 删除节点 module1(biz1) 被拒 1302102', code_of(r) == 1302102, f'code={code_of(r)}')

# B3: 升级为全业务授权 → biz1 操作放行
rc, out, err = run_cli('policy', 'grant-scenario', '--user', 'tom', '--scenario', 'topo-admin')
check('B3 CLI grant topo-admin(全业务) 退出0', rc == 0, f'rc={rc}')
sc, r = call('POST', '/api/v1/topo/biz/1/set', TOM, {'names': ['e2e_biz1_nowok']})
check('B3 升级全业务后：biz1 创建集群过网关', code_of(r) == 0, f'code={code_of(r)}')
sc, r = call('PUT', '/api/v1/topo/node/set/1', TOM, {'bk_set_name': 'e2e_edit_nowok'})
check('B3 升级全业务后：编辑节点 set1(biz1) 过网关', code_of(r) == 0, f'code={code_of(r)}')
call('PUT', '/api/v1/topo/node/set/1', ADMIN, {'bk_set_name': '空闲机池'})  # 还原

# B4: 撤销全业务 → 还原基线
rc, out, err = run_cli('policy', 'revoke', '--user', 'tom', '--res-type', 'biz_topology',
                       '--action', 'create,update,delete')
check('B4 CLI revoke topo-admin(全业务) 退出0', rc == 0, f'rc={rc}')
sc, r = call('POST', '/api/v1/topo/biz/2/set', TOM, {'names': ['e2e_after_revoke']})
check('B4 撤销后：biz2 创建集群复现 1302102', code_of(r) == 1302102, f'code={code_of(r)}')

# B5: 清理 B1 授予的 biz2 专属策略，避免污染真实库
rc, out, err = run_cli('policy', 'revoke', '--user', 'tom', '--res-type', 'biz_topology',
                       '--action', 'create,update,delete', '--biz-id', '2')
check('B5 清理 biz2 专属策略（不误伤全业务/其他 biz）', rc == 0, f'rc={rc} {err[-100:]}')

# 清理 Part B 测试数据（删除节点需 bk_biz_id 参数）
if set2_id:
    call('DELETE', f'/api/v1/topo/node/set/{set2_id}', ADMIN, params={'bk_biz_id': 2})
if mod_id:
    call('DELETE', f'/api/v1/topo/node/module/{mod_id}', ADMIN, params={'bk_biz_id': 2})
# 清掉 B3 创建的 biz1 测试集群（名含 e2e_%）
con = sqlite3.connect('cmdb_dev.db'); con.row_factory = sqlite3.Row
for s in con.execute("SELECT bk_set_id, bk_biz_id FROM cc_SetBase WHERE bk_set_name LIKE 'e2e_%'"):
    call('DELETE', f"/api/v1/topo/node/set/{s['bk_set_id']}", ADMIN, params={'bk_biz_id': s['bk_biz_id']})
con.close()

# ---------------------------------------------------------------------------
print(f'\n===== 结果：PASS={PASS} FAIL={FAIL} =====')
sys.exit(1 if FAIL else 0)
