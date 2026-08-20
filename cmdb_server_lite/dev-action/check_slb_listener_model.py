import duckdb
import sys

# 连接数据库
db = duckdb.connect('cmdb.duckdb')

try:
    # 查询所有模型，找到SLB监听器
    print("=== 查询所有模型 ===")
    models = db.execute("SELECT bk_obj_id, bk_obj_name FROM cc_ObjDes ORDER BY bk_obj_name").fetchall()
    for model in models:
        print(f"bk_obj_id: {model[0]}, bk_obj_name: {model[1]}")
    
    print("\n=== 查询包含'slb'或'listener'或'监听器'的模型 ===")
    models = db.execute("""
        SELECT bk_obj_id, bk_obj_name 
        FROM cc_ObjDes 
        WHERE bk_obj_id LIKE '%slb%' OR bk_obj_id LIKE '%listener%' 
              OR bk_obj_name LIKE '%slb%' OR bk_obj_name LIKE '%listener%'
              OR bk_obj_name LIKE '%监听器%'
        ORDER BY bk_obj_name
    """).fetchall()
    for model in models:
        print(f"bk_obj_id: {model[0]}, bk_obj_name: {model[1]}")

    # 如果找到模型，显示其现有属性
    if models:
        for model in models:
            obj_id = model[0]
            print(f"\n=== 模型 {obj_id} 的现有属性 ===")
            attrs = db.execute("""
                SELECT bk_property_id, bk_property_name, bk_property_type, bk_property_index
                FROM cc_ObjAttDes 
                WHERE bk_obj_id = ? 
                ORDER BY bk_property_index
            """, [obj_id]).fetchall()
            for attr in attrs:
                print(f"  {attr[0]}: {attr[1]} ({attr[2]}) - index: {attr[3]}")
            
            # 查看实例表结构
            table_name = f'cc_ObjectBase_0_pub_{obj_id}'
            print(f"\n=== 实例表 {table_name} 的结构 ===")
            try:
                columns = db.execute(f"PRAGMA table_info({table_name})").fetchall()
                for col in columns:
                    print(f"  {col[1]} ({col[2]})")
            except Exception as e:
                print(f"  无法查看表结构: {e}")

finally:
    db.close()
