import duckdb

# 连接数据库
db = duckdb.connect('cmdb.duckdb')

try:
    print("=== 检查 cc_ObjAttDes 表中的 bk_slb_listener 属性 ===")
    attrs = db.execute("""
        SELECT bk_property_id, bk_property_name, bk_property_type, bk_property_index
        FROM cc_ObjAttDes 
        WHERE bk_obj_id = 'bk_slb_listener'
        ORDER BY bk_property_index
    """).fetchall()
    
    for attr in attrs:
        print(f"  {attr[0]}: {attr[1]} ({attr[2]}) - index: {attr[3]}")
    
    print("\n=== 检查实例表中的 service_time 字段 ===")
    columns = db.execute("PRAGMA table_info(cc_ObjectBase_0_pub_bk_slb_listener)").fetchall()
    for col in columns:
        if col[1] == 'service_time':
            print(f"✅ 字段 {col[1]} ({col[2]}) 存在")

finally:
    db.close()
