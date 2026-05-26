import duckdb
import sys
from datetime import datetime

# 连接数据库
db = duckdb.connect('cmdb.duckdb')

try:
    print("=== 查看 cc_ObjClassification 表数据 ===")
    data = db.execute("SELECT * FROM cc_ObjClassification").fetchall()
    
    if data:
        for row in data:
            print(f"  {row}")
    else:
        print("  没有数据，需要插入分组数据！")
        
        # 插入分组数据
        print("\n=== 正在插入分组数据 ===")
        
        current_time = datetime.now()
        
        # 网络设备分组
        db.execute("""
            INSERT INTO cc_ObjClassification (
                id, bk_classification_id, bk_classification_name, bk_classification_type,
                bk_classification_icon, bk_ishidden, ispre, creator, modifier,
                create_time, last_time, bk_supplier_account
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            1, 'bk_network', '网络设备', 'inner', 'icon-cc-network',
            False, True, 'admin', 'admin', current_time, current_time, '0'
        ])
        
        # 主机管理分组
        db.execute("""
            INSERT INTO cc_ObjClassification (
                id, bk_classification_id, bk_classification_name, bk_classification_type,
                bk_classification_icon, bk_ishidden, ispre, creator, modifier,
                create_time, last_time, bk_supplier_account
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            2, 'bk_host_manage', '主机', 'inner', 'icon-cc-host',
            False, True, 'admin', 'admin', current_time, current_time, '0'
        ])
        
        # 负载均衡分组
        db.execute("""
            INSERT INTO cc_ObjClassification (
                id, bk_classification_id, bk_classification_name, bk_classification_type,
                bk_classification_icon, bk_ishidden, ispre, creator, modifier,
                create_time, last_time, bk_supplier_account
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            3, 'bk_loadbalance', '负载均衡', 'inner', 'icon-cc-loadbalance',
            False, True, 'admin', 'admin', current_time, current_time, '0'
        ])
        
        print("  ✅ 成功插入 3 个分组！")
        
        # 再次查询验证
        print("\n=== 验证插入结果 ===")
        data = db.execute("SELECT * FROM cc_ObjClassification").fetchall()
        for row in data:
            print(f"  {row}")
    
    # 更新 cc_ObjDes 表中的 obj_sort_number
    print("\n=== 更新模型排序 ===")
    
    # 网络设备分组下的模型
    db.execute("UPDATE cc_ObjDes SET obj_sort_number = 1 WHERE bk_obj_id = 'bk_switch'")
    
    # 主机管理分组下的模型
    db.execute("UPDATE cc_ObjDes SET obj_sort_number = 1 WHERE bk_obj_id = 'bk_host'")
    
    # 负载均衡分组下的模型
    db.execute("UPDATE cc_ObjDes SET obj_sort_number = 1 WHERE bk_obj_id = 'bk_slb'")
    db.execute("UPDATE cc_ObjDes SET obj_sort_number = 2 WHERE bk_obj_id = 'bk_slb_server'")
    db.execute("UPDATE cc_ObjDes SET obj_sort_number = 3 WHERE bk_obj_id = 'bk_slb_listener'")
    
    print("  ✅ 模型排序已更新！")

finally:
    db.close()
