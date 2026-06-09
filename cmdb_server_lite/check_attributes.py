#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.db.engine import get_connection
from sqlalchemy import text
import json

print("检查交换机属性数据...")

conn = get_connection()
try:
    # 查询交换机的属性
    attributes = conn.execute(
        text("SELECT bk_property_id, bk_property_name, bk_isapi, bk_issystem, editable, isreadonly, bk_ishidden FROM cc_ObjAttDes WHERE bk_obj_id = 'bk_switch' ORDER BY bk_property_index")
    ).fetchall()
    
    print(f"找到 {len(attributes)} 个属性：")
    for attr in attributes:
        prop_id = attr[0]
        prop_name = attr[1]
        bk_isapi = attr[2]
        bk_issystem = attr[3]
        editable = attr[4]
        isreadonly = attr[5]
        bk_ishidden = attr[6]
        
        print(f"  {prop_id} ({prop_name}):")
        print(f"    bk_isapi: {bk_isapi}")
        print(f"    bk_issystem: {bk_issystem}")
        print(f"    editable: {editable}")
        print(f"    isreadonly: {isreadonly}")
        print(f"    bk_ishidden: {bk_ishidden}")
        
finally:
    conn.close()
