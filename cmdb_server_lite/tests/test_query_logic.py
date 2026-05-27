#!/usr/bin/env python3
"""
模拟 getExistInstAssociation 行为
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_query():
    print("=" * 80)
    print("测试查询逻辑")
    print("=" * 80)
    
    print("\n1. 以 SLB 实例 2 作为源对象查询关联:")
    print("-" * 80)
    
    # 模拟前端 getExistInstAssociation 查询:
    params1 = {
        "bk_obj_id": "bk_slb",
        "condition": {
            "bk_obj_id": "bk_slb", 
            "bk_inst_id": 2,
            "bk_asst_obj_id": "bk_slb_server",
            "bk_asst_id": "to",
            "bk_obj_asst_id": "bk_slb_to_bk_slb_server"
        }
    }
    
    print(f"查询参数: {json.dumps(params1, indent=2, ensure_ascii=False)}")
    
    resp1 = requests.post(f"{BASE_URL}/find/instassociation", json=params1)
    print(f"结果: {len(resp1.json()['info'])}条")
    for a in resp1.json()['info']:
        print(f"  - {a}")

    print("\n2. 查询条件简化后:")
    print("-" * 80)
    
    params2 = {
        "bk_obj_id": "bk_slb", 
        "condition": {
            "bk_inst_id": 2,
            "bk_obj_asst_id": "bk_slb_to_bk_slb_server"
        }
    }
    
    print(f"查询参数: {json.dumps(params2, indent=2, ensure_ascii=False)}")
    resp2 = requests.post(f"{BASE_URL}/find/instassociation", json=params2)
    print(f"结果: {len(resp2.json()['info'])}条")
    for a in resp2.json()['info']:
        print(f"  - {a}")

if __name__ == "__main__":
    test_query()
