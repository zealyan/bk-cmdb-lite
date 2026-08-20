#!/usr/bin/env python3
"""
测试关联创建流程
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_create_flow():
    print("=" * 80)
    print("测试关联创建流程")
    print("=" * 80)
    
    # 1. 查询 SLB 实例 1 的当前关联
    print("\n步骤1: 查询 SLB 实例 1 的关联")
    print("-" * 80)
    
    params = {
        "bk_obj_id": "bk_slb",
        "condition": {
            "bk_inst_id": 1
        }
    }
    
    print(f"查询参数: {json.dumps(params, indent=2, ensure_ascii=False)}")
    
    resp = requests.post(f"{BASE_URL}/find/instassociation", json=params)
    data = resp.json()
    assocs = data.get("info", [])
    
    print(f"找到 {len(assocs)} 条关联:")
    for a in assocs:
        print(f"  - ID: {a['id']}, 目标: {a['bk_asst_obj_id']}/{a['bk_asst_inst_id']}")
    
    # 2. 测试创建新的关联 (SLB 1 -> SLB Server ID 2)
    print("\n步骤2: 创建新的关联 (SLB 1 -> SLB Server ID 2)")
    print("-" * 80)
    
    # 获取模型关联信息
    obj_assoc_resp = requests.post(f"{BASE_URL}/find/objectassociation", json={})
    obj_assocs = obj_assoc_resp.json()
    
    # 找到 bk_slb 到 bk_slb_server 的关联
    slb_to_server = None
    for obj in obj_assocs:
        if obj['bk_obj_id'] == 'bk_slb' and obj['target_obj_id'] == 'bk_slb_server':
            slb_to_server = obj
            break
    
    if not slb_to_server:
        print("错误: 找不到 SLB 到 SLB Server 的关联定义")
        return
    
    print(f"找到关联定义: {slb_to_server['bk_obj_asst_id']}")
    
    create_params = {
        "bk_obj_id": "bk_slb",               # 源模型
        "bk_inst_id": 1,                       # 源实例 ID
        "bk_asst_obj_id": "bk_slb_server",    # 目标模型
        "bk_asst_inst_id": 2,                 # 目标实例 ID
        "bk_obj_asst_id": slb_to_server['bk_obj_asst_id'],  # 模型关联 ID
        "bk_relation_type_id": slb_to_server['bk_asst_id']   # 关联类型 ID
    }
    
    print(f"创建参数: {json.dumps(create_params, indent=2, ensure_ascii=False)}")
    
    create_resp = requests.post(f"{BASE_URL}/create/instassociation", json=create_params)
    print(f"创建响应状态: {create_resp.status_code}")
    print(f"创建响应: {create_resp.json()}")
    
    # 3. 验证创建结果
    print("\n步骤3: 验证创建结果")
    print("-" * 80)
    
    verify_resp = requests.post(f"{BASE_URL}/find/instassociation", json=params)
    verify_data = verify_resp.json()
    verify_assocs = verify_data.get("info", [])
    
    print(f"现在有 {len(verify_assocs)} 条关联:")
    for a in verify_assocs:
        print(f"  - ID: {a['id']}, 目标: {a['bk_asst_obj_id']}/{a['bk_asst_inst_id']}")
    
    # 4. 检查是否包含了新创建的关联
    new_assoc = [a for a in verify_assocs if a['bk_asst_inst_id'] == 2]
    if new_assoc:
        print(f"\n✅ 验证成功: SLB 1 与 SLB Server 2 的关联已创建!")
        print(f"   关联 ID: {new_assoc[0]['id']}")
    else:
        print(f"\n❌ 验证失败: SLB 1 与 SLB Server 2 的关联未找到!")

if __name__ == "__main__":
    test_create_flow()
