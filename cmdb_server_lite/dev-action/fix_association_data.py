#!/usr/bin/env python3
"""
修复associations表中的数据不一致问题
1. 为缺失关联的实例创建关联记录
2. 删除指向不存在实例的孤立关联记录
"""

import duckdb

DB_PATH = '/workspace/bk-cmdb/cmdb_server_lite/cmdb.duckdb'

def fix_association_data():
    """修复关联数据"""
    print("="*60)
    print("🔧 修复associations表数据不一致问题")
    print("="*60)

    db = duckdb.connect(DB_PATH)

    # 1. 检查所有SLB实例
    print("\n【1. 检查SLB实例】")
    slbs = db.execute('SELECT id, bk_lb_name FROM cc_ObjectBase_0_pub_bk_slb ORDER BY id').fetchall()
    print(f"  总数: {len(slbs)}")
    for slb in slbs[:3]:
        print(f"  ID={slb[0]}, name={slb[1]}")
    if len(slbs) > 3:
        print(f"  ... 还有 {len(slbs)-3} 条")

    # 2. 检查后端服务器实例及其关联状态
    print("\n【2. 检查后端服务器关联状态】")
    servers = db.execute('SELECT id, bk_server_name, bk_slb_id FROM cc_ObjectBase_0_pub_bk_slb_server ORDER BY id').fetchall()
    print(f"  总数: {len(servers)}")

    # 3. 检查监听器实例及其关联状态
    print("\n【3. 检查监听器关联状态】")
    listeners = db.execute('SELECT id, bk_listener_name, bk_slb_id FROM cc_ObjectBase_0_pub_bk_slb_listener ORDER BY id').fetchall()
    print(f"  总数: {len(listeners)}")

    # 4. 统计每个SLB的关联情况
    print("\n【4. 统计关联情况】")
    all_assocs = db.execute('''
        SELECT a.id, a.bk_obj_id, a.bk_inst_id, a.bk_asst_obj_id, a.bk_asst_inst_id
        FROM cc_InstAsst_0_pub a
        WHERE a.bk_obj_id = 'bk_slb'
    ''').fetchall()

    # 按SLB ID分组统计
    from collections import defaultdict
    assoc_stats = defaultdict(lambda: {'servers': [], 'listeners': []})

    for assoc in all_assocs:
        slb_id = assoc[2]
        asst_type = assoc[3]
        asst_id = assoc[4]
        if asst_type == 'bk_slb_server':
            assoc_stats[slb_id]['servers'].append(asst_id)
        elif asst_type == 'bk_slb_listener':
            assoc_stats[slb_id]['listeners'].append(asst_id)

    # 5. 检查并修复SLB ID=1的数据
    print("\n【5. 检查SLB ID=1的数据】")
    slb_id = 1

    # 获取SLB ID=1的后端服务器
    servers_of_slb = [s for s in servers if s[2] == str(slb_id)]
    print(f"  后端服务器实例数: {len(servers_of_slb)}")

    # 获取SLB ID=1的监听器
    listeners_of_slb = [l for l in listeners if l[2] == str(slb_id)]
    print(f"  监听器实例数: {len(listeners_of_slb)}")

    # 获取当前关联
    current_server_assocs = assoc_stats[slb_id]['servers']
    current_listener_assocs = assoc_stats[slb_id]['listeners']
    print(f"  当前后端服务器关联数: {len(current_server_assocs)}")
    print(f"  当前监听器关联数: {len(current_listener_assocs)}")

    # 6. 找出缺失的关联
    print("\n【6. 找出缺失的关联】")

    # 后端服务器缺失关联
    server_instance_ids = [s[0] for s in servers_of_slb]
    missing_server_ids = [sid for sid in server_instance_ids if sid not in current_server_assocs]
    print(f"  缺失的后端服务器关联: {len(missing_server_ids)}条")
    if missing_server_ids:
        print(f"    缺失的ID: {missing_server_ids}")

    # 监听器缺失关联
    listener_instance_ids = [l[0] for l in listeners_of_slb]
    missing_listener_ids = [lid for lid in listener_instance_ids if lid not in current_listener_assocs]
    print(f"  缺失的监听器关联: {len(missing_listener_ids)}条")
    if missing_listener_ids:
        print(f"    缺失的ID: {missing_listener_ids}")

    # 7. 找出无效的关联（指向不存在的实例）
    print("\n【7. 检查无效的关联】")

    # 后端服务器无效关联
    invalid_server_ids = [sid for sid in current_server_assocs if sid not in server_instance_ids]
    print(f"  无效的后端服务器关联: {len(invalid_server_ids)}条")
    if invalid_server_ids:
        print(f"    无效的ID: {invalid_server_ids}")

    # 监听器无效关联
    invalid_listener_ids = [lid for lid in current_listener_assocs if lid not in listener_instance_ids]
    print(f"  无效的监听器关联: {len(invalid_listener_ids)}条")
    if invalid_listener_ids:
        print(f"    无效的ID: {invalid_listener_ids}")

    # 8. 修复数据
    print("\n【8. 修复数据】")

    # 删除无效的后端服务器关联
    if invalid_server_ids:
        for sid in invalid_server_ids:
            db.execute('''
                DELETE FROM cc_InstAsst_0_pub
                WHERE bk_obj_id = 'bk_slb' AND bk_inst_id = ? AND bk_asst_obj_id = 'bk_slb_server' AND bk_asst_inst_id = ?
            ''', [slb_id, sid])
        print(f"  ✓ 已删除 {len(invalid_server_ids)} 条无效后端服务器关联")

    # 删除无效的监听器关联
    if invalid_listener_ids:
        for lid in invalid_listener_ids:
            db.execute('''
                DELETE FROM cc_InstAsst_0_pub
                WHERE bk_obj_id = 'bk_slb' AND bk_inst_id = ? AND bk_asst_obj_id = 'bk_slb_listener' AND bk_asst_inst_id = ?
            ''', [slb_id, lid])
        print(f"  ✓ 已删除 {len(invalid_listener_ids)} 条无效监听器关联")

    # 创建缺失的后端服务器关联
    if missing_server_ids:
        # 获取relation_type_id
        relation_type = db.execute('''
            SELECT bk_relation_type_id FROM cc_InstAsst_0_pub
            WHERE bk_obj_id = 'bk_slb' AND bk_asst_obj_id = 'bk_slb_server'
            LIMIT 1
        ''').fetchone()
        relation_type_id = relation_type[0] if relation_type else 'bk_slb_server_rel'

        for sid in missing_server_ids:
            # 使用序列获取下一个ID
            next_id = db.execute('SELECT COALESCE(MAX(id), 0) + 1 FROM cc_InstAsst_0_pub').fetchone()[0]
            db.execute('''
                INSERT INTO cc_InstAsst_0_pub (id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id, bk_relation_type_id)
                VALUES (?, 'bk_slb', ?, 'bk_slb_server', ?, ?)
            ''', [next_id, slb_id, sid, relation_type_id])

        print(f"  ✓ 已创建 {len(missing_server_ids)} 条后端服务器关联")

    # 创建缺失的监听器关联
    if missing_listener_ids:
        # 获取relation_type_id
        relation_type = db.execute('''
            SELECT bk_relation_type_id FROM cc_InstAsst_0_pub
            WHERE bk_obj_id = 'bk_slb' AND bk_asst_obj_id = 'bk_slb_listener'
            LIMIT 1
        ''').fetchone()
        relation_type_id = relation_type[0] if relation_type else 'bk_slb_listener_rel'

        for lid in missing_listener_ids:
            # 使用序列获取下一个ID
            next_id = db.execute('SELECT COALESCE(MAX(id), 0) + 1 FROM cc_InstAsst_0_pub').fetchone()[0]
            db.execute('''
                INSERT INTO cc_InstAsst_0_pub (id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id, bk_relation_type_id)
                VALUES (?, 'bk_slb', ?, 'bk_slb_listener', ?, ?)
            ''', [next_id, slb_id, lid, relation_type_id])

        print(f"  ✓ 已创建 {len(missing_listener_ids)} 条监听器关联")

    if not invalid_server_ids and not invalid_listener_ids and not missing_server_ids and not missing_listener_ids:
        print("  ✓ 无需修复，数据已一致")

    # 9. 验证修复结果
    print("\n【9. 验证修复结果】")
    final_assocs = db.execute('''
        SELECT a.bk_asst_obj_id, COUNT(*) as cnt
        FROM associations a
        WHERE a.bk_obj_id = 'bk_slb' AND a.bk_inst_id = ?
        GROUP BY a.bk_asst_obj_id
    ''', [slb_id]).fetchall()

    print(f"  SLB ID={slb_id} 的关联记录:")
    for assoc in final_assocs:
        print(f"    {assoc[0]}: {assoc[1]}条")

    # 验证是否与实例数量一致
    final_server_count = sum([a[1] for a in final_assocs if a[0] == 'bk_slb_server'])
    final_listener_count = sum([a[1] for a in final_assocs if a[0] == 'bk_slb_listener'])

    if final_server_count == len(server_instance_ids) and final_listener_count == len(listener_instance_ids):
        print(f"\n✅ 修复完成！SLB ID={slb_id} 的关联数据已与实例数量一致")
    else:
        print(f"\n⚠️ 仍有差异: 期望(服务器:{len(server_instance_ids)}, 监听器:{len(listener_instance_ids)}), 实际(服务器:{final_server_count}, 监听器:{final_listener_count})")

    db.close()
    print("\n" + "="*60)
    print("修复完成！")
    print("="*60)

if __name__ == '__main__':
    fix_association_data()
