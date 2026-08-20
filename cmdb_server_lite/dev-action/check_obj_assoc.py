#!/usr/bin/env python3
"""
检查模型关联数据
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def check_data():
    print("=" * 80)
    print("检查模型关联数据")
    print("=" * 80)
    
    # 查询模型关联
    print("\n查询模型关联 (cc_ObjAsst)")
    print("-" * 80)
    
    response = requests.post(f"{BASE_URL}/find/objectassociation", json={})
    obj_asst_types = response.json()
    print(f"返回类型: {type(obj_asst_types)}")
    print(f"响应内容: {json.dumps(obj_asst_types, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    check_data()
