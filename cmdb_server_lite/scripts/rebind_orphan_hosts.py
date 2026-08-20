"""
数据修复：cc_ModuleHostConfig 悬空绑定（指向不存在的 module/set）。
根因：早期 seed 用硬编码小 ID 写入绑定，与后来 generate_id 创建的 module/set 不同源。
修复：把每 biz 的悬空绑定主机重绑到该 biz 空闲机池下的「空闲机」(default=1) module，
      对齐真实 CMDB「无业务归属主机自动进空闲机池」语义。
幂等：目标 module 必须存在（按 biz 空闲机池校验），不存在则跳过并告警。
用法：cd cmdb_server_lite && python3 scripts/rebind_orphan_hosts.py
"""
import logging
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
import sys
sys.path.insert(0, '.')
from app import create_app
from app.db.executor import query_all, query_one, execute

app = create_app()


def get_idle_module(biz_id):
    """返回 biz 空闲机池下 default=1 的 module（空闲机）：(set_id, module_id) 或 None。"""
    row = query_one(
        "SELECT s.bk_set_id, m.bk_module_id FROM cc_SetBase s "
        "JOIN cc_ModuleBase m ON m.bk_set_id = s.bk_set_id AND m.bk_supplier_account = s.bk_supplier_account "
        "WHERE s.bk_biz_id = :b AND s.bk_supplier_account = '0' AND s.\"default\" = 1 "
        "AND m.\"default\" = 1 AND m.bk_biz_id = :b "
        "ORDER BY m.bk_module_id LIMIT 1",
        {'b': biz_id})
    return (row['bk_set_id'], row['bk_module_id']) if row else None


with app.app_context():
    # 1) 找出所有悬空绑定（module 不存在）
    orphan_rows = query_all("""
        SELECT m.id, m.bk_biz_id, m.bk_host_id, m.bk_module_id, m.bk_set_id
        FROM cc_ModuleHostConfig m
        LEFT JOIN cc_ModuleBase mb ON mb.bk_module_id = m.bk_module_id AND mb.bk_supplier_account = m.bk_supplier_account
        WHERE mb.bk_module_id IS NULL
        ORDER BY m.bk_biz_id, m.bk_host_id
    """)
    print(f"悬空绑定总数: {len(orphan_rows)}")

    by_biz = {}
    for r in orphan_rows:
        by_biz.setdefault(r['bk_biz_id'], []).append(r)

    total_ok = 0
    for biz_id, rows in sorted(by_biz.items()):
        idle = get_idle_module(biz_id)
        if not idle:
            print(f"  [warn] biz{biz_id} 无空闲机池 module，跳过 {len(rows)} 条")
            continue
        set_id, module_id = idle
        execute(
            "UPDATE cc_ModuleHostConfig SET bk_module_id = :mid, bk_set_id = :sid "
            "WHERE bk_biz_id = :b AND bk_supplier_account = '0' AND bk_module_id IN ("
            "SELECT bk_module_id FROM cc_ModuleHostConfig WHERE bk_biz_id = :b AND bk_supplier_account = '0' "
            "AND bk_module_id NOT IN (SELECT bk_module_id FROM cc_ModuleBase))",
            {'mid': module_id, 'sid': set_id, 'b': biz_id})
        total_ok += len(rows)
        print(f"  biz{biz_id}: 重绑 {len(rows)} 台主机 -> 空闲机池 set{set_id}/module{module_id}")

    # 2) 校验：不应再有悬空绑定
    left = query_one("""
        SELECT COUNT(*) AS c FROM cc_ModuleHostConfig m
        LEFT JOIN cc_ModuleBase mb ON mb.bk_module_id = m.bk_module_id AND mb.bk_supplier_account = m.bk_supplier_account
        WHERE mb.bk_module_id IS NULL
    """)['c']
    print()
    print(f"修复完成: 重绑 {total_ok} 条；剩余悬空绑定 = {left}（应为 0）")

    # 3) 按 biz 汇总新绑定
    print()
    print("=== 修复后各 biz 主机绑定（module 维度）===")
    rows = query_all("""
        SELECT m.bk_biz_id, m.bk_module_id, mb.bk_module_name, m.bk_set_id, COUNT(DISTINCT m.bk_host_id) AS hosts
        FROM cc_ModuleHostConfig m
        LEFT JOIN cc_ModuleBase mb ON mb.bk_module_id = m.bk_module_id AND mb.bk_supplier_account = m.bk_supplier_account
        GROUP BY m.bk_biz_id, m.bk_module_id, m.bk_set_id ORDER BY m.bk_biz_id
    """)
    for r in rows:
        print(f"  biz{r['bk_biz_id']}: module{r['bk_module_id']} {r['bk_module_name']} set{r['bk_set_id']} = {r['hosts']} 台")
