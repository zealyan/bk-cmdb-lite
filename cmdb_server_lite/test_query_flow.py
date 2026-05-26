#!/usr/bin/env python3
"""
测试关联查询流程，模拟前端的 getExistInstAssociation
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_query_flow():
    print("=" * 80)
    print("测试关联查询流程（模拟前端 getExistInstAssociation）")
    print("=" * 80)
    
    # 场景：SLB 实例 18，查询其与 SLB Server 的关联
    
    # 1. 查询 SLB 18 当前的关联（使用不同条件）
    print("\n测试1: 使用 bk_inst_id=18 查询")
    print("-" * 80)
    
    params1 = {
        "bk_obj_id": "bk_slb",
        "condition": {
            "bk_inst_id": 18,
            "bk_obj_asst_id": "bk_slb_to_bk_slb_server"
        }
    }
    
    print(f"查询参数: {json.dumps(params1, indent=2, ensure_ascii=False)}")
    
    resp1 = requests.post(f"{BASE_URL}/find/instassociation", json=params1)
    data1 = resp1.json()
    assocs1 = data1.get("info", [])
    
    print(f"找到 {len(assocs1)} 条关联:")
    for a in assocs1:
        print(f"  - ID: {a['id']}, 目标: {a['bk_asst_obj_id']}/{a['bk_asst_inst_id']}")
    
    # 2. 测试不同查询条件
    print("\n测试2: 只使用 bk_inst_id=18 查询")
    print("-" * 80)
    
    params2 = {
        "bk_obj_id": "bk_slb",
        "condition": {
            "bk_inst_id": 18
        }
    }
    
    print(f"查询参数: {json.dumps(params2, indent=2, ensure_ascii=False)}")
    
    resp2 = requests.post(f"{BASE_URL}/find/instassociation", json=params2)
    data2 = resp2.json()
    assocs2 = data2.get("info", [])
    
    print(f"找到 {len(assocs2)} 条关联:")
    for a in assocs2:
        print(f"  - ID: {a['id']}, 目标: {a['bk_asst_obj_id']}/{a['bk_asst_inst_id']}")
    
    # 3. 检查是否存在我们创建的关联（ID=162）
    print("\n测试3: 检查是否存在 ID=162 的关联")
    print("-" * 80)
    
    if assocs2:
        found = [a for a in assocs2 if a['id'] == 162]
        if found:
            print(f"✅ 找到 ID=162 的关联:")
            print(json.dumps(found[0], indent=2, ensure_ascii=False))
        else:
            print("❌ 未找到 ID=162 的关联")
            print(f"所有关联 ID: {[a['id'] for a in assocs2]}")
    else:
        print("❌ 没有查询到任何关联")
    
    # 4. 查询所有 SLB 18 的关联（不过滤 bk_obj_asst_id）
    print("\n测试4: 查询 SLB 18 的所有关联（不过滤关联类型）")
    print("-" * 80)
    
    params4 = {
        "condition": {
            "bk_obj_id": "bk_slb",
            "bk_inst_id": 18
        }
    }
    
    print(f"查询参数: {json.dumps(params4, indent=2, ensure_ascii=False)}")
    
    resp4 = requests.post(f"{BASE_URL}/find/instassociation", json=params4)
    data4 = resp4.json()
    assocs4 = data4.get("info", [])
    
    print(f"找到 {len(assocs4)} 条关联:")
    for a in assocs4:
        print(f"  - ID: {a['id']}, 源: {a['bk_obj_id']}/{a['bk_inst_id']}, 目标: {a['bk_asst_obj_id']}/{a['bk_asst_inst_id']}, 关联类型: {a['bk_obj_asst_id']}")
    
    # 5. 列出所有 cc_InstAsst_0_pub 表中的记录
    print("\n测试5: 直接查询数据库表 cc_InstAsst_0_pub")
    print("-" * 80)
    
    # 这个测试需要直接访问数据库，但我们可以通过查询所有记录来模拟
    params5 = {
        "condition": {
            "bk_obj_id": "bk_slb",
            "bk_inst_id": 18
        }
    }
    
    resp5 = requests.post(f"{BASE_URL}/find/instassociation", json=params5)
    data5 = resp5.json()
    assocs5 = data5.get("info", [])
    
    print(f"表中共有 {len(assocs5)} 条 SLB 18 的关联记录")
    
    # 检查 ID=162 是否存在
    found_162 = [a for a in assocs5 if a['id'] == 162]
    if found_162:
        print(f"\n✅ ID=162 存在于数据库表中!")
        print(f"   关联详情:")
        print(f"   - 源: {found_162[0]['bk_obj_id']}/{found_162[0]['bk_inst_id']}")
        print(f"   - 目标: {found_162[0]['bk_asst_obj_id']}/{found_162[0]['bk_asst_inst_id']}")
        print(f"   - 模型关联: {found_162[0]['bk_obj_asst_id']}")
        print(f"   - 关联类型: {found_162[0]['bk_relation_type_id']}")
    else:
        print(f"\n❌ ID=162 不存在于数据库表中!")
    
    print("\n" + "=" * 80)
    print("结论")
    print("=" * 80)
    
    if found_162:
        print("✅ 数据库中已正确保存了关联 ID=162")
        print("✅ 问题可能在于前端查询条件不匹配")
    else:
        print("❌ 数据库中没有关联 ID=162，数据保存失败")

if __name__ == "__main__":
    test_query_flow()
