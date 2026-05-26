import duckdb
import uuid
from datetime import datetime

# 连接数据库
db = duckdb.connect('cmdb.duckdb')

try:
    obj_id = 'bk_slb_listener'
    property_id = 'service_time'
    property_name = '服务启动时间'
    property_type = 'time'  # 日期时间类型
    
    # 1. 获取下一个ID
    max_id_result = db.execute("SELECT MAX(id) FROM cc_ObjAttDes").fetchone()
    next_id = (max_id_result[0] or 0) + 1
    
    # 2. 获取下一个属性索引
    max_index_result = db.execute("""
        SELECT MAX(bk_property_index) 
        FROM cc_ObjAttDes 
        WHERE bk_obj_id = ? AND bk_property_index < 9000
    """, [obj_id]).fetchone()
    next_index = (max_index_result[0] or 0) + 1
    
    print(f"=== 准备新增属性 ===")
    print(f"模型ID: {obj_id}")
    print(f"属性ID: {property_id}")
    print(f"属性名称: {property_name}")
    print(f"属性类型: {property_type}")
    print(f"属性索引: {next_index}")
    print(f"记录ID: {next_id}")
    
    # 3. 插入属性定义到 cc_ObjAttDes 表
    _id = f"{obj_id}.{property_id}"
    current_time = datetime.now()
    
    db.execute("""
        INSERT INTO cc_ObjAttDes (
            _id, id, bk_obj_id, bk_property_id, bk_property_name, 
            bk_property_type, bk_property_group, isrequired, bk_ispassword, 
            bk_ishidden, isreadonly, bk_isapi, bk_issystem, option, 
            unit, placeholder, editable, ispre, bk_property_index, 
            creator, modifier, create_time, last_time, bk_supplier_account, 
            bk_property_option, default_columns
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        _id, next_id, obj_id, property_id, property_name,
        property_type, 'default', False, False,
        False, False, False, False, None,
        '', '', True, False, next_index,
        'admin', 'admin', current_time, current_time, '0',
        None, None
    ])
    
    print(f"\n✅ 已成功在 cc_ObjAttDes 表中新增属性定义")
    
    # 4. 为实例表新增字段
    table_name = f'cc_ObjectBase_0_pub_{obj_id}'
    print(f"\n=== 为实例表 {table_name} 新增字段 ===")
    
    # 检查字段是否已存在
    columns = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    column_names = [col[1] for col in columns]
    
    if property_id in column_names:
        print(f"⚠️ 字段 {property_id} 已存在，跳过新增")
    else:
        # 新增字段，使用 TIMESTAMP 类型
        db.execute(f"ALTER TABLE {table_name} ADD COLUMN {property_id} TIMESTAMP")
        print(f"✅ 已成功在 {table_name} 表中新增字段 {property_id}")
    
    # 5. 验证结果
    print(f"\n=== 验证新增属性 ===")
    attr = db.execute("""
        SELECT bk_property_id, bk_property_name, bk_property_type, bk_property_index
        FROM cc_ObjAttDes 
        WHERE bk_obj_id = ? AND bk_property_id = ?
    """, [obj_id, property_id]).fetchone()
    
    if attr:
        print(f"✅ 属性定义验证成功:")
        print(f"  - 属性ID: {attr[0]}")
        print(f"  - 属性名称: {attr[1]}")
        print(f"  - 属性类型: {attr[2]}")
        print(f"  - 属性索引: {attr[3]}")
    else:
        print(f"❌ 属性定义验证失败")
    
    # 验证字段
    columns = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    column_found = False
    for col in columns:
        if col[1] == property_id:
            print(f"✅ 表字段验证成功:")
            print(f"  - 字段名: {col[1]}")
            print(f"  - 字段类型: {col[2]}")
            column_found = True
            break
    
    if not column_found:
        print(f"❌ 表字段验证失败")
    
    print(f"\n=== 完成！ ===")
    print(f"请重启后端和前端服务以查看变更")

finally:
    db.close()
