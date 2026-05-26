#!/usr/bin/env python3
"""
修复associations表中的孤立记录
检查并删除指向不存在实例的关联记录
"""

import duckdb

DB_PATH = '/workspace/bk-cmdb/cmdb_server_lite/cmdb.duckdb'

def check_and_fix_associations():
    """检查并修复associations表"""
    print("="*60)
    print("🔧 检查并修复associations表")
    print("="*60)

    db = duckdb.connect(DB_PATH)

    # 1. 检查所有关联记录
    print("\n【1. 检查所有关联记录】")
    all_assocs = db.execute('''
        SELECT id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id, bk_relation_type_id
        FROM cc_InstAsst_0_pub
        ORDER BY bk_obj_id, bk_inst_id
    ''').fetchall()
    print(f"  总关联记录: {len(all_assocs)}")

    # 2. 按对象类型分组统计
    print("\n【2. 按对象类型统计】")
    obj_stats = db.execute('''
        SELECT bk_obj_id, bk_asst_obj_id, COUNT(*) as cnt
        FROM cc_InstAsst_0_pub
        GROUP BY bk_obj_id, bk_asst_obj_id
        ORDER BY bk_obj_id, bk_asst_obj_id
    ''').fetchall()
    for stat in obj_stats:
        print(f"  {stat[0]} -> {stat[1]}: {stat[2]}条")

    # 3. 检查SLB ID=1的所有关联
    print("\n【3. SLB ID=1 的所有关联】")
    slb_assocs = db.execute('''
        SELECT * FROM cc_InstAsst_0_pub
        WHERE bk_obj_id = ? AND bk_inst_id = ?
    ''', ['bk_slb', 1]).fetchall()
    print(f"  总数: {len(slb_assocs)}")

    # 4. 检查后端服务器关联
    print("\n【4. 检查后端服务器关联】")
    server_assocs = [a for a in slb_assocs if a[3] == 'bk_slb_server']
    print(f"  后端服务器关联数: {len(server_assocs)}")

    # 5. 检查这些关联的服务器是否真的存在
    print("\n【5. 验证关联的后端服务器是否存在】")
    valid_server_assocs = []
    invalid_server_assocs = []

    for assoc in server_assocs:
        assoc_id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id, bk_relation_type_id = assoc
        # 检查实例是否存在
        result = db.execute('SELECT id FROM cc_ObjectBase_0_pub_bk_slb_server WHERE id = ?', [bk_asst_inst_id]).fetchone()
        if result:
            valid_server_assocs.append(assoc)
        else:
            invalid_server_assocs.append(assoc)
            print(f"  ⚠️ 孤立记录: associations.id={assoc_id}, bk_asst_inst_id={bk_asst_inst_id}")

    print(f"  有效关联: {len(valid_server_assocs)}条")
    print(f"  无效关联: {len(invalid_server_assocs)}条")

    # 6. 检查监听器关联
    print("\n【6. 检查监听器关联】")
    listener_assocs = [a for a in slb_assocs if a[3] == 'bk_slb_listener']
    print(f"  监听器关联数: {len(listener_assocs)}")

    # 7. 验证这些监听器是否真的存在
    print("\n【7. 验证关联的监听器是否存在】")
    valid_listener_assocs = []
    invalid_listener_assocs = []

    for assoc in listener_assocs:
        assoc_id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id, bk_relation_type_id = assoc
        # 检查实例是否存在
        result = db.execute('SELECT id FROM cc_ObjectBase_0_pub_bk_slb_listener WHERE id = ?', [bk_asst_inst_id]).fetchone()
        if result:
            valid_listener_assocs.append(assoc)
        else:
            invalid_listener_assocs.append(assoc)
            print(f"  ⚠️ 孤立记录: associations.id={assoc_id}, bk_asst_inst_id={bk_asst_inst_id}")

    print(f"  有效关联: {len(valid_listener_assocs)}条")
    print(f"  无效关联: {len(invalid_listener_assocs)}条")

    # 8. 统计实际的实例数量
    print("\n【8. 实际实例数量（通过bk_slb_id字段）】")
    actual_servers = db.execute('SELECT COUNT(*) FROM cc_ObjectBase_0_pub_bk_slb_server WHERE bk_slb_id = ?', ['1']).fetchone()[0]
    actual_listeners = db.execute('SELECT COUNT(*) FROM cc_ObjectBase_0_pub_bk_slb_listener WHERE bk_slb_id = ?', ['1']).fetchone()[0]
    print(f"  实际后端服务器: {actual_servers}条")
    print(f"  实际监听器: {actual_listeners}条")

    # 9. 清理孤立记录
    print("\n【9. 清理孤立记录】")
    total_invalid = len(invalid_server_assocs) + len(invalid_listener_assocs)
    if total_invalid > 0:
        print(f"  发现 {total_invalid} 条孤立记录，准备清理...")

        # 删除孤立的后端服务器关联
        if invalid_server_assocs:
            invalid_ids = [a[0] for a in invalid_server_assocs]
            for invalid_id in invalid_ids:
                db.execute('DELETE FROM cc_InstAsst_0_pub WHERE id = ?', [invalid_id])
            print(f"  ✓ 已删除 {len(invalid_ids)} 条孤立后端服务器关联")

        # 删除孤立的监听器关联
        if invalid_listener_assocs:
            invalid_ids = [a[0] for a in invalid_listener_assocs]
            for invalid_id in invalid_ids:
                db.execute('DELETE FROM cc_InstAsst_0_pub WHERE id = ?', [invalid_id])
            print(f"  ✓ 已删除 {len(invalid_ids)} 条孤立监听器关联")
    else:
        print("  ✓ 无需清理，关联记录都是有效的")

    # 10. 验证修复结果
    print("\n【10. 验证修复结果】")
    remaining_assocs = db.execute('''
        SELECT * FROM cc_InstAsst_0_pub
        WHERE bk_obj_id = ? AND bk_inst_id = ?
    ''', ['bk_slb', 1]).fetchall()
    remaining_servers = [a for a in remaining_assocs if a[3] == 'bk_slb_server']
    remaining_listeners = [a for a in remaining_assocs if a[3] == 'bk_slb_listener']

    print(f"  剩余后端服务器关联: {len(remaining_servers)}条")
    print(f"  剩余监听器关联: {len(remaining_listeners)}条")
    print(f"  总关联记录: {len(remaining_assocs)}条")

    # 验证是否与实际实例数量一致
    if len(remaining_servers) == actual_servers and len(remaining_listeners) == actual_listeners:
        print("\n✅ 关联数据已修复，与实际实例数量一致！")
    else:
        print("\n⚠️ 仍有差异，需要进一步检查")

    db.close()
    print("\n" + "="*60)
    print("修复完成！")
    print("="*60)

if __name__ == '__main__':
    check_and_fix_associations()
