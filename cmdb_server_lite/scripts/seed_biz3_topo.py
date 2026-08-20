#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 biz3（bk_biz_id=3，业务名「正式环境」）批量生成自定义主线拓扑测试数据：

  主线链：biz -> sys(应用系统) -> subsys(应用子系统) -> set -> module

规模（≤1 万节点）：
  - 50 个 sys 实例（bk_parent_id = 3）
  - 400 个 subsys 实例（每个 sys 下 5~10 个，精确合计 400）
  - 每个 subsys 下 2~4 个 set（名称取自 临平/杭州/东新/合肥，同一 subsys 内唯一）
  - 每个 set 下 2~3 个 module（名称取自 springboot/mysql/otherapp/tomcat/nginx，唯一）
  预计总节点 ≈ 4650（sys 50 + subsys 400 + set ~1200 + module ~3000）

父子关系通过各实例表的 bk_parent_id 串联（对齐 topo_service 的树拼装逻辑）。
直接走 app 的 executor/execute_many 批量写入，避免逐条 create_instance 的开销。

用法：在 cmdb_server_lite 目录下运行  python3 scripts/seed_biz3_topo.py
"""
import os
import sys
import time
import random

# 确保在项目根目录下运行，保证 sqlite 相对路径与 settings 一致
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.db.executor import execute_many          # noqa: E402
from app.utils.tools import generate_id          # noqa: E402
from app.service.instance_service import InstanceService  # noqa: E402

random.seed(42)
BIZ_ID = 3
SUP = '0'
NOW = time.strftime('%Y-%m-%d %H:%M:%S')

SYS_TBL = InstanceService._get_table_name('sys')           # cc_ObjectBase_0_pub_sys
SUBSYS_TBL = InstanceService._get_table_name('subsys')     # cc_ObjectBase_0_pub_subsys
SET_TBL = 'cc_SetBase'
MODULE_TBL = 'cc_ModuleBase'

SET_NAME_POOL = ['临平', '杭州', '东新', '合肥']
MODULE_NAME_POOL = ['springboot', 'mysql', 'otherapp', 'tomcat', 'nginx']

N_SYS = 50
N_SUBSYS_TOTAL = 400


def chunked(rows, size=5000):
    for i in range(0, len(rows), size):
        yield rows[i:i + size]


def unique_names(pool, n):
    """从 pool 中取 n 个名称，保证同一父节点下唯一（超出 pool 长度时追加序号后缀）。"""
    names = []
    used = set()
    for k in range(n):
        bn = pool[k % len(pool)]
        if bn in used:
            s = 1
            cand = f"{bn}{s}"
            while cand in used:
                s += 1
                cand = f"{bn}{s}"
            name = cand
        else:
            name = bn
        used.add(name)
        names.append(name)
    return names


def clean_biz3():
    """清理 biz3 旧拓扑实例（sys/subsys/set/module），保证脚本可重复执行。"""
    for tbl in [SYS_TBL, SUBSYS_TBL, SET_TBL, MODULE_TBL]:
        execute_many(f'DELETE FROM "{tbl}" WHERE bk_biz_id = :biz', [{'biz': BIZ_ID}])
    print('[0/4] 已清理 biz3 旧拓扑实例')


def build_idle_pool():
    """重建 biz3 空闲机池（default=1），对齐 biz2 结构：空闲机池 set + 空闲机 module。

    注意：clean_biz3() 会连同空闲机池一起删除，若不重建，biz3 将失去 default 集群，
    主机转移/空闲机池功能与「default 标识」相关的逻辑都会失效。
    """
    set_id = generate_id()
    mod_id = generate_id()
    execute_many(
        'INSERT INTO "cc_SetBase" (bk_set_id, bk_set_name, bk_parent_id, bk_biz_id, "default", '
        'bk_set_desc, bk_set_env, bk_service_status, bk_supplier_account, create_time, last_time, creator, modifier) '
        'VALUES (:sid, :name, :biz, :biz, 1, NULL, \'3\', \'1\', :sup, :now, :now, :user, :user)',
        [{'sid': set_id, 'name': '空闲机池', 'biz': BIZ_ID, 'sup': SUP, 'now': NOW, 'user': 'admin'}])
    execute_many(
        'INSERT INTO "cc_ModuleBase" (bk_module_id, bk_module_name, bk_parent_id, bk_set_id, bk_biz_id, "default", '
        'bk_supplier_account, create_time, last_time, creator, modifier) '
        'VALUES (:mid, :name, :sid, :sid, :biz, 1, :sup, :now, :now, :user, :user)',
        [{'mid': mod_id, 'name': '空闲机', 'sid': set_id, 'biz': BIZ_ID, 'sup': SUP, 'now': NOW, 'user': 'admin'}])
    print(f'[5/4] 空闲机池     = set-{set_id}(空闲机池) + module-{mod_id}(空闲机)')


def main():
    t0 = time.time()
    clean_biz3()
    # ── 1) sys：50 个，父 = biz3 ──
    sys_rows = []
    sys_ids = []
    for i in range(N_SYS):
        iid = generate_id()
        sys_ids.append(iid)
        sys_rows.append({
            'bk_inst_id': iid,
            'bk_inst_name': f"应用系统{i:04d}",
            'bk_supplier_account': SUP,
            'bk_obj_id': 'sys',
            'bk_biz_id': BIZ_ID,
            'bk_parent_id': BIZ_ID,           # biz 的实例主键即 bk_biz_id
            'default': 0,
            'create_time': NOW,
            'last_time': NOW,
        })
    for batch in chunked(sys_rows):
        execute_many(
            f'INSERT INTO "{SYS_TBL}" '
            '(bk_inst_id, bk_inst_name, bk_supplier_account, bk_obj_id, '
            'bk_biz_id, bk_parent_id, "default", create_time, last_time) '
            'VALUES (:bk_inst_id, :bk_inst_name, :bk_supplier_account, :bk_obj_id, '
            ':bk_biz_id, :bk_parent_id, :default, :create_time, :last_time)',
            batch)
    print(f"[1/4] sys         = {len(sys_rows)}  ({time.time()-t0:.1f}s)")

    # ── 2) subsys：分配到 1000 个 sys，每个 5~20，合计精确 7000 ──
    counts = [5] * N_SYS
    remain = N_SUBSYS_TOTAL - sum(counts)  # 2000
    while remain > 0:
        i = random.randrange(N_SYS)
        if counts[i] < 20:
            counts[i] += 1
            remain -= 1
    subsys_rows = []
    for si, cnt in enumerate(counts):
        parent = sys_ids[si]
        for k in range(cnt):
            iid = generate_id()
            subsys_rows.append({
                'bk_inst_id': iid,
                'bk_inst_name': f"应用子系统-{sys_ids[si]}-{k}",
                'bk_supplier_account': SUP,
                'bk_obj_id': 'subsys',
                'bk_biz_id': BIZ_ID,
                'bk_parent_id': parent,
                'default': 0,
                'create_time': NOW,
                'last_time': NOW,
            })
    for batch in chunked(subsys_rows):
        execute_many(
            f'INSERT INTO "{SUBSYS_TBL}" '
            '(bk_inst_id, bk_inst_name, bk_supplier_account, bk_obj_id, '
            'bk_biz_id, bk_parent_id, "default", create_time, last_time) '
            'VALUES (:bk_inst_id, :bk_inst_name, :bk_supplier_account, :bk_obj_id, '
            ':bk_biz_id, :bk_parent_id, :default, :create_time, :last_time)',
            batch)
    print(f"[2/4] subsys      = {len(subsys_rows)}  ({time.time()-t0:.1f}s)")

    # ── 3) set：每个 subsys 下 2~8 个，名称取自 临平/杭州/东新/合肥（同一 subsys 内唯一）──
    set_rows = []
    set_ids = []          # 与 set_rows 一一对应，供 module 引用
    set_parent_ids = []   # 对应 subsys 的 bk_inst_id
    for row in subsys_rows:
        parent = row['bk_inst_id']
        n = random.randint(2, 4)
        for name in unique_names(SET_NAME_POOL, n):
            iid = generate_id()
            set_rows.append({
                'bk_set_id': iid,
                'bk_set_name': name,
                'bk_parent_id': parent,
                'bk_biz_id': BIZ_ID,
                'bk_supplier_account': SUP,
                'create_time': NOW,
                'last_time': NOW,
            })
            set_ids.append(iid)
            set_parent_ids.append(parent)
    for batch in chunked(set_rows):
        execute_many(
            'INSERT INTO "cc_SetBase" '
            '(bk_set_id, bk_set_name, bk_parent_id, bk_biz_id, '
            'bk_supplier_account, create_time, last_time) '
            'VALUES (:bk_set_id, :bk_set_name, :bk_parent_id, :bk_biz_id, '
            ':bk_supplier_account, :create_time, :last_time)',
            batch)
    print(f"[3/4] set         = {len(set_rows)}  ({time.time()-t0:.1f}s)")

    # ── 4) module：每个 set 下 2~3 个，名称取自 springboot/mysql/otherapp/tomcat/nginx（唯一）──
    module_rows = []
    for sid, parent in zip(set_ids, set_parent_ids):
        n = random.randint(2, 3)
        for name in random.sample(MODULE_NAME_POOL, n):
            iid = generate_id()
            module_rows.append({
                'bk_module_id': iid,
                'bk_module_name': name,
                'bk_parent_id': sid,      # 父实例 = set 的 bk_set_id
                'bk_set_id': sid,
                'bk_biz_id': BIZ_ID,
                'bk_supplier_account': SUP,
                'create_time': NOW,
                'last_time': NOW,
            })
    for batch in chunked(module_rows):
        execute_many(
            'INSERT INTO "cc_ModuleBase" '
            '(bk_module_id, bk_module_name, bk_parent_id, bk_set_id, bk_biz_id, '
            'bk_supplier_account, create_time, last_time) '
            'VALUES (:bk_module_id, :bk_module_name, :bk_parent_id, :bk_set_id, '
            ':bk_biz_id, :bk_supplier_account, :create_time, :last_time)',
            batch)
    print(f"[4/4] module      = {len(module_rows)}  ({time.time()-t0:.1f}s)")
    build_idle_pool()
    print(f"完成。总实例数 ≈ {len(sys_rows)+len(subsys_rows)+len(set_rows)+len(module_rows)+2}（含空闲机池 set+module）")


if __name__ == '__main__':
    main()
