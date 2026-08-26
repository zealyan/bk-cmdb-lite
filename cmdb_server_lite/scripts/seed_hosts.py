#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重建种子主机的业务拓扑挂载关系（修复脚本 / 可重复执行）。

背景
----
早期 migrate 把 21 台主机写死绑定到硬编码模块 ID（1/4/100/101/110/200/300），
而主线拓扑模块经 generate_id 重新生成后 ID 漂移（实际在 53000+ 区间），
导致这 21 条绑定全部悬空。rebind_orphan_hosts.py 曾把悬空主机临时塞回空闲机池，
但丢失了「主机应归属业务模块（web/api/db/app/test）」的原始语义。

本脚本直接复用 migrate.py 中重构后的 seed_host_bindings()：
- 按 (业务, 集群名, 模块名) 语义解析真实 bk_module_id/bk_set_id；
- 目标模块/集群缺失时自动补全创建；
- 先清旧绑定再落库，幂等可重复执行。

用法（在 cmdb_server_lite 目录下）：
    python3 scripts/seed_hosts.py
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.migrate.migrate import DatabaseMigrator, HOST_BINDING_SPEC  # noqa: E402
from app.db.executor import query_all, query_one                       # noqa: E402


def verify():
    """校验：无悬空绑定，且 21 台主机均落到预期业务模块。"""
    orphan = query_one("""
        SELECT COUNT(*) AS c FROM cc_ModuleHostConfig m
        LEFT JOIN cc_ModuleBase mb ON mb.bk_module_id = m.bk_module_id
            AND mb.bk_supplier_account = m.bk_supplier_account
        WHERE mb.bk_module_id IS NULL
    """)['c']
    total = query_one("SELECT COUNT(*) AS c FROM cc_ModuleHostConfig")['c']
    distinct_hosts = query_one(
        "SELECT COUNT(DISTINCT bk_host_id) AS c FROM cc_ModuleHostConfig")['c']
    print(f"\n[校验] 绑定总数={total}  去重主机={distinct_hosts}  悬空绑定={orphan}（应为 0）")
    print("[校验] 各 biz 主机数（module 维度）：")
    for r in query_all("""
        SELECT m.bk_biz_id, mb.bk_module_name, m.bk_set_id,
               COUNT(DISTINCT m.bk_host_id) AS hosts
        FROM cc_ModuleHostConfig m
        LEFT JOIN cc_ModuleBase mb ON mb.bk_module_id = m.bk_module_id
            AND mb.bk_supplier_account = m.bk_supplier_account
        GROUP BY m.bk_biz_id, m.bk_module_id, m.bk_set_id
        ORDER BY m.bk_biz_id, mb.bk_module_name
    """):
        print(f"  biz{r['bk_biz_id']}: {r['bk_module_name']} = {r['hosts']} 台")
    return orphan == 0 and distinct_hosts == len(HOST_BINDING_SPEC)


def main():
    t0 = time.time()
    migrator = DatabaseMigrator()
    # 21 台种子主机已存在于 cc_HostBase（如缺失可先跑 run_migrate.py）；
    # 此处仅重建挂载关系，按业务拓扑语义解析/补全模块，幂等。
    migrator.seed_host_bindings()
    print(f"[完成] 种子主机挂载重建耗时 {time.time() - t0:.1f}s")
    ok = verify()
    if ok:
        print("\n✅ 21 台种子主机均已正确挂载到业务拓扑模块，无悬空绑定。")
    else:
        print("\n❌ 仍存在悬空绑定或数量不符，请检查上方校验输出。")
        sys.exit(1)


if __name__ == '__main__':
    main()
