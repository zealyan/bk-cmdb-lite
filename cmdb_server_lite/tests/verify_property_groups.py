#!/usr/bin/env python3
"""验证属性分组表和数据"""
from app.db.engine import get_connection
from sqlalchemy import text

def verify_property_groups():
    conn = get_connection()
    try:
        # 检查 cc_PropertyGroup 表是否存在
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='cc_PropertyGroup'"))
        table_exists = result.fetchone()
        if not table_exists:
            print("❌ cc_PropertyGroup 表不存在")
            return
        
        print("✅ cc_PropertyGroup 表存在")
        
        # 查询分组数据
        result = conn.execute(text("SELECT bk_obj_id, bk_group_id, bk_group_name, bk_group_index, bk_isdefault FROM cc_PropertyGroup ORDER BY bk_obj_id, bk_group_index"))
        groups = result.fetchall()
        
        print(f"\n✅ 查询到 {len(groups)} 个属性分组:")
        for group in groups:
            print(f"  - 模型: {group[0]}, 分组ID: {group[1]}, 名称: {group[2]}, 索引: {group[3]}, 默认: {group[4]}")
        
        # 查询属性的分组情况
        result = conn.execute(text("""
            SELECT bk_obj_id, bk_property_id, bk_property_name, bk_property_group 
            FROM cc_ObjAttDes 
            WHERE bk_property_group != 'default' 
            ORDER BY bk_obj_id, bk_property_id
        """))
        properties = result.fetchall()
        
        print(f"\n✅ 查询到 {len(properties)} 个属性更新了分组:")
        for prop in properties:
            print(f"  - 模型: {prop[0]}, 属性ID: {prop[1]}, 名称: {prop[2]}, 分组: {prop[3]}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    verify_property_groups()
