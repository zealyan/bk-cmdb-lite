#!/usr/bin/env python3
"""
检查模型关联和关联类型数据
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def check_data():
    print("=" * 80)
    print("检查关联类型数据")
    print("=" * 80)
    
    # 查询关联类型
    print("\n1. 查询关联类型 (cc_AsstDes)")
    print("-" * 80)
    
    response = requests.post(f"{BASE_URL}/find/associationtype", json={})
    asst_types = response.json()
    print(f"找到 {len(asst_types.get('info', []))} 个关联类型")
    for t in asst_types.get('info', []):
        print(json.dumps(t, indent=2, ensure_ascii=False))
    
    # 查询模型关联
    print("\n2. 查询模型关联 (cc_ObjAsst)")
    print("-" * 80)
    
    response = requests.post(f"{BASE_URL}/find/objectassociation", json={})
    obj_asst_types = response.json()
    print(f"找到 {len(obj_asst_types.get('info', []))} 个模型关联")
    for t in obj_asst_types.get('info', []):
        print(json.dumps(t, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    check_data()
