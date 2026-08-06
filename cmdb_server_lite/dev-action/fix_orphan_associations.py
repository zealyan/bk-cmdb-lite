#!/usr/bin/env python3
"""
清理孤立的实例关联记录（孤儿记录）。

孤儿记录定义：关联的一端（源实例 bk_obj_id/bk_inst_id 或
目标实例 bk_asst_obj_id/bk_asst_inst_id）所指向的实例在实例表中并不存在。

原项目 bk-cmdb 在创建关联前会校验两端实例必须存在，且删除实例时会级联
清理关联；本 lite 分支种子数据（associations/index.json）为 bk_slb 源实例
生成了指向 1-10 的关联，但 bk_slb 实际只有 1-8 个实例，导致 bk_slb/9、10
成为孤儿源，进而在 web-server 等实例的“关联我的”分组中出现
“负载均衡 (N)” 统计但列表为空的虚假分组。

本脚本扫描所有 cc_InstAsst_* 分表，删除两端实例缺失的记录，并输出报告。
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'cmdb_dev.db') if os.path.exists(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cmdb_dev.db')
) else 'cmdb_dev.db'

BUILTIN_TABLE_MAP = {
    'biz': 'cc_ApplicationBase',
    'set': 'cc_SetBase',
    'module': 'cc_ModuleBase',
    'host': 'cc_HostBase',
    'bk_host': 'cc_HostBase',
}
BUILTIN_ID_FIELD_MAP = {
    'biz': 'bk_biz_id',
    'set': 'bk_set_id',
    'module': 'bk_module_id',
    'host': 'bk_host_id',
    'bk_host': 'bk_host_id',
}


def inst_table(model):
    return BUILTIN_TABLE_MAP.get(model, f'cc_ObjectBase_0_pub_{model}')


def inst_id_field(model):
    return BUILTIN_ID_FIELD_MAP.get(model, 'bk_inst_id')


def exists(con, model, inst_id):
    t = inst_table(model)
    f = inst_id_field(model)
    try:
        cur = con.execute(f'SELECT 1 FROM "{t}" WHERE "{f}" = :id LIMIT 1',
                          {'id': int(inst_id)})
        return cur.fetchone() is not None
    except Exception:
        return False


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    # 收集所有关联分表
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cc_InstAsst_0_pub_%'")]

    orphan_ids = set()
    for t in tables:
        for r in con.execute(
                f'SELECT id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id '
                f'FROM "{t}"'):
            src_ok = exists(con, r['bk_obj_id'], r['bk_inst_id'])
            dst_ok = exists(con, r['bk_asst_obj_id'], r['bk_asst_inst_id'])
            if not src_ok or not dst_ok:
                orphan_ids.add(r['id'])

    print(f"发现孤儿关联记录 id 数: {len(orphan_ids)}")
    if not orphan_ids:
        print("无需清理。")
        return

    # 从所有分表按 id 删除（关联记录在每个相关分表里各有副本）
    placeholders = ','.join('?' * len(orphan_ids))
    total_deleted = 0
    for t in tables:
        cur = con.execute(f'DELETE FROM "{t}" WHERE id IN ({placeholders})',
                          list(orphan_ids))
        total_deleted += cur.rowcount
    con.commit()
    print(f"已删除孤儿记录副本行数: {total_deleted}")

    # 校验：再次扫描，确认无孤儿
    remaining = 0
    for t in tables:
        for r in con.execute(
                f'SELECT id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id '
                f'FROM "{t}"'):
            if not exists(con, r['bk_obj_id'], r['bk_inst_id']) or \
               not exists(con, r['bk_asst_obj_id'], r['bk_asst_inst_id']):
                remaining += 1
    print(f"清理后残留孤儿记录行数: {remaining}")
    con.close()
    print("清理完成。")


if __name__ == '__main__':
    main()
