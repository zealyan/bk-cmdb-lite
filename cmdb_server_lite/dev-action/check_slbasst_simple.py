#!/usr/bin/env python3
"""
检查 SLB 实例 2、3 的关联数据情况
"""

import duckdb
import json

DB_PATH = '/workspace/bk-cmdb/cmdb_server_lite/cmdb.duckdb'

def get_db():
    conn = duckdb.connect(DB_PATH)
    return conn

def check_associations():
    print("=" * 80)
    print("检查 SLB 实例关联数据检查")
    print("=" * 80)
    
    conn = get_db()
    
    # 查询所有 SLB 相关关联
    print("\n1. 查询所有 SLB 相关关联数据")
    print("-" * 80)
    
    sql = """
        SELECT 
            id, _id, bk_obj_id, bk_inst_id, 
            bk_asst_obj_id, bk_asst_inst_id,
            bk_obj_asst_id, bk_relation_type_id
        FROM cc_InstAsst_0_pub 
        WHERE bk_obj_id = 'bk_slb' OR bk_asst_obj_id = 'bk_slb'
        ORDER BY id
    """
    
    result = conn.execute(sql).fetchall()
    columns = [desc[0] for desc in conn.description]
    
    print(f"找到 {len(result)} 条 SLB 相关关联记录:")
    print()
    
    for row in result:
        assoc = dict(zip(columns, row))
        print(f"  ID: {assoc['id']}")
        print(f"  Source: {assoc['bk_obj_id']} / {assoc['bk_inst_id']}")
        print(f"  Target: {assoc['bk_asst_obj_id']} / {assoc['bk_asst_inst_id']}")
        print(f"  Association: {assoc['bk_obj_asst_id']}")
        print(f"  Relation: {assoc['bk_relation_type_id']}")
        print(f"  _id: {assoc['_id']}")
        print()
    
    # 检查 SLB 实例 2 的关联
    print("\n2. 检查 SLB 实例 2 的关联")
    print("-" * 80)
    
    sql_slb2 = """
        SELECT * FROM cc_InstAsst_0_pub 
        WHERE (bk_obj_id = 'bk_slb' AND bk_inst_id = 2) 
           OR (bk_asst_obj_id = 'bk_slb' AND bk_asst_inst_id = 2)
    """
    
    result_slb2 = conn.execute(sql_slb2).fetchall()
    columns_slb2 = [desc[0] for desc in conn.description]
    
    print(f"SLB 实例 2 有 {len(result_slb2)} 条关联:")
    for row in result_slb2:
        assoc = dict(zip(columns_slb2, row))
        print(f"  - {json.dumps(assoc, ensure_ascii=False, indent=4)}")
    
    # 检查 SLB 实例 3 的关联
    print("\n3. 检查 SLB 实例 3 的关联")
    print("-" * 80)
    
    sql_slb3 = """
        SELECT * FROM cc_InstAsst_0_pub 
        WHERE (bk_obj_id = 'bk_slb' AND bk_inst_id = 3) 
           OR (bk_asst_obj_id = 'bk_slb' AND bk_asst_inst_id = 3)
    """
    
    result_slb3 = conn.execute(sql_slb3).fetchall()
    columns_slb3 = [desc[0] for desc in conn.description]
    
    print(f"SLB 实例 3 有 {len(result_slb3)} 条关联:")
    for row in result_slb3:
        assoc = dict(zip(columns_slb3, row))
        print(f"  - {json.dumps(assoc, ensure_ascii=False, indent=4)}")
    
    # 检查模型关联类型
    print("\n4. 检查模型关联类型")
    print("-" * 80)
    
    sql_obj_assoc = """
        SELECT * FROM cc_ObjAsst ORDER BY id
    """
    
    result_obj_assoc = conn.execute(sql_obj_assoc).fetchall()
    columns_obj_assoc = [desc[0] for desc in conn.description]
    
    print(f"找到 {len(result_obj_assoc)} 个模型关联类型:")
    for row in result_obj_assoc:
        assoc = dict(zip(columns_obj_assoc, row))
        print(f"  - {json.dumps(assoc, ensure_ascii=False, indent=4)}")
    
    # 检查关联类型
    print("\n5. 检查关联类型定义")
    print("-" * 80)
    
    sql_assoc_type = """
        SELECT * FROM cc_AsstDes ORDER BY id
    """
    
    result_assoc_type = conn.execute(sql_assoc_type).fetchall()
    columns_assoc_type = [desc[0] for desc in conn.description]
    
    print(f"找到 {len(result_assoc_type)} 个关联类型:")
    for row in result_assoc_type:
        assoc = dict(zip(columns_assoc_type, row))
        print(f"  - {json.dumps(assoc, ensure_ascii=False, indent=4)}")
    
    # 统计汇总
    print("\n6. 统计汇总")
    print("-" * 80)
    
    sql_total = "SELECT COUNT(*) as total FROM cc_InstAsst_0_pub"
    result_total = conn.execute(sql_total).fetchone()
    print(f"总关联数量: {result_total[0]}")
    
    sql_slb_total = """
        SELECT COUNT(*) as total FROM cc_InstAsst_0_pub 
        WHERE bk_obj_id = 'bk_slb' OR bk_asst_obj_id = 'bk_slb'
    """
    result_slb_total = conn.execute(sql_slb_total).fetchone()
    print(f"SLB 相关关联: {result_slb_total[0]}")
    
    conn.close()

if __name__ == "__main__":
    check_associations()
