"""诊断：主机与业务 topo 关联关系数据完整性。
检查 cc_HostBase / cc_ModuleHostConfig / cc_ModuleBase / cc_SetBase / cc_ApplicationBase 之间的引用完整性。
"""
import logging
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
import sys
sys.path.insert(0, '.')
from app import create_app
from app.db.executor import query_all, query_one
app = create_app()
with app.app_context():
    print("=== 1. 基础数据量 ===")
    for t in ['cc_HostBase', 'cc_ApplicationBase', 'cc_SetBase', 'cc_ModuleBase', 'cc_ModuleHostConfig']:
        n = query_one(f'SELECT COUNT(*) AS c FROM "{t}"')['c']
        print(f"  {t}: {n}")

    print()
    print("=== 2. cc_ModuleHostConfig 按 biz 分组 ===")
    rows = query_all("SELECT bk_biz_id, COUNT(*) AS c, COUNT(DISTINCT bk_host_id) AS hosts, COUNT(DISTINCT bk_module_id) AS mods FROM cc_ModuleHostConfig GROUP BY bk_biz_id ORDER BY bk_biz_id")
    for r in rows:
        print(f"  biz{r['bk_biz_id']}: 绑定 {r['c']} 条, 主机 {r['hosts']}, 模块 {r['mods']}")

    print()
    print("=== 3. 悬空绑定（module 在 cc_ModuleBase 中不存在）===")
    rows = query_all("""
        SELECT m.bk_biz_id, m.bk_module_id, m.bk_host_id FROM cc_ModuleHostConfig m
        LEFT JOIN cc_ModuleBase mb ON mb.bk_module_id = m.bk_module_id AND mb.bk_supplier_account = m.bk_supplier_account
        WHERE mb.bk_module_id IS NULL
        ORDER BY m.bk_biz_id, m.bk_module_id
    """)
    print(f"  悬空 module 绑定: {len(rows)} 条")
    seen = {}
    for r in rows:
        key = (r['bk_biz_id'], r['bk_module_id'])
        seen[key] = seen.get(key, 0) + 1
    for (biz, mid), c in sorted(seen.items()):
        print(f"    biz{biz} module{mid}: {c} 台主机（模块不存在！）")

    print()
    print("=== 4. 悬空 host（cc_HostBase 中不存在）===")
    rows = query_all("""
        SELECT m.bk_biz_id, m.bk_module_id, m.bk_host_id FROM cc_ModuleHostConfig m
        LEFT JOIN cc_HostBase hb ON hb.bk_host_id = m.bk_host_id AND hb.bk_supplier_account = m.bk_supplier_account
        WHERE hb.bk_host_id IS NULL
        ORDER BY m.bk_biz_id
    """)
    print(f"  悬空 host 绑定: {len(rows)} 条")

    print()
    print("=== 5. module 的 bk_set_id 指向的 set 是否存在 ===")
    rows = query_all("""
        SELECT mb.bk_module_id, mb.bk_module_name, mb.bk_set_id, mb.bk_biz_id FROM cc_ModuleBase mb
        LEFT JOIN cc_SetBase sb ON sb.bk_set_id = mb.bk_set_id AND sb.bk_supplier_account = mb.bk_supplier_account
        WHERE mb.bk_supplier_account = '0' AND sb.bk_set_id IS NULL
        ORDER BY mb.bk_biz_id
    """)
    print(f"  module 引用不存在 set: {len(rows)} 条")
    seen = {}
    for r in rows:
        key = (r['bk_biz_id'], r['bk_set_id'])
        seen[key] = seen.get(key, 0) + 1
    for (biz, sid), c in sorted(seen.items()):
        print(f"    biz{biz} set{sid}: {c} 个 module（set 不存在！）")

    print()
    print("=== 6. set 的 bk_parent_id 链（父是否存在）===")
    rows = query_all("""
        SELECT sb.bk_set_id, sb.bk_set_name, sb.bk_parent_id, sb.bk_biz_id, sb."default"
        FROM cc_SetBase sb WHERE sb.bk_supplier_account = '0' ORDER BY sb.bk_biz_id, sb.bk_set_id
    """)
    # 主线链：biz->sys->subsys->set->module，set 的父应为 subsys；空闲机池(default=1) 父应为 biz
    orphan_sets = []
    biz_ids = {r['bk_biz_id'] for r in query_all("SELECT bk_biz_id FROM cc_ApplicationBase WHERE bk_supplier_account='0'")}
    subsys_ids = {r['bk_inst_id'] for r in query_all("SELECT bk_inst_id FROM cc_ObjectBase_0_pub_subsys WHERE bk_supplier_account='0'")}
    for r in rows:
        pid = r['bk_parent_id']
        biz = r['bk_biz_id']
        if r['default'] == 1:
            ok = pid in biz_ids  # 空闲机池父=biz
        else:
            ok = pid in subsys_ids  # 普通 set 父=subsys
        if not ok:
            orphan_sets.append((biz, r['bk_set_id'], r['bk_set_name'], 'idle' if r['default'] == 1 else 'normal', pid))
    print(f"  父链异常 set: {len(orphan_sets)} 个")
    for o in orphan_sets[:20]:
        print(f"    biz{o[0]} set{o[1]} {o[2]} [{o[3]}] parent={o[4]}")

    print()
    print("=== 7. module 的 bk_parent_id 与 bk_set_id 一致性 ===")
    rows = query_all("""
        SELECT mb.bk_module_id, mb.bk_module_name, mb.bk_parent_id, mb.bk_set_id, mb.bk_biz_id FROM cc_ModuleBase mb
        WHERE mb.bk_supplier_account = '0' AND mb.bk_parent_id != mb.bk_set_id
        ORDER BY mb.bk_biz_id LIMIT 10
    """)
    print(f"  module bk_parent_id != bk_set_id: {len(rows)} 条(仅显示前10)")
    for r in rows:
        print(f"    biz{r['bk_biz_id']} module{r['bk_module_id']} {r['bk_module_name']} parent={r['bk_parent_id']} set={r['bk_set_id']}")

    print()
    print("=== 8. 各 biz 有效主机数（绑定到有效 module）===")
    rows = query_all("""
        SELECT m.bk_biz_id, COUNT(DISTINCT m.bk_host_id) AS hosts FROM cc_ModuleHostConfig m
        JOIN cc_ModuleBase mb ON mb.bk_module_id = m.bk_module_id AND mb.bk_supplier_account = m.bk_supplier_account
        GROUP BY m.bk_biz_id ORDER BY m.bk_biz_id
    """)
    for r in rows:
        print(f"  biz{r['bk_biz_id']}: 有效主机 {r['hosts']} 台")
