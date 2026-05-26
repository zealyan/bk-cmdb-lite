#!/usr/bin/env python3
"""
测试关联数据：验证创建关联后数据是否正确保存到数据库
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_create_association():
    """测试创建关联"""
    # SLB 实例关联到 SLB 服务
    # 假设 SLB 实例 ID = 18，要关联到 SLB 服务 ID = 1
    params = {
        "bk_obj_id": "bk_slb",          # 源模型
        "bk_inst_id": 18,               # 源实例 ID
        "bk_asst_obj_id": "bk_slb_service",  # 目标模型
        "bk_asst_inst_id": 1,           # 目标实例 ID
        "bk_obj_asst_id": "slb_to_service",   # 关联类型 ID
        "bk_relation_type_id": 2        # 关联类型（对应 belong）
    }

    print("=" * 60)
    print("测试创建关联")
    print("=" * 60)
    print(f"请求参数: {json.dumps(params, indent=2, ensure_ascii=False)}")

    try:
        response = requests.post(f"{BASE_URL}/create/instassociation", json=params)
        print(f"状态码: {response.status_code}")
        print(f"响应数据: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"错误: {e}")
        return None

def test_find_association(inst_id=18, asst_inst_id=None):
    """测试查询关联"""
    # 查询 SLB 实例 18 的所有关联
    params = {
        "bk_obj_id": "bk_slb",          # 源模型
        "condition": {
            "bk_inst_id": inst_id,      # 源实例 ID
        }
    }

    if asst_inst_id is not None:
        params["condition"]["bk_asst_inst_id"] = asst_inst_id

    print("\n" + "=" * 60)
    print(f"测试查询关联 (inst_id={inst_id}, asst_inst_id={asst_inst_id})")
    print("=" * 60)
    print(f"请求参数: {json.dumps(params, indent=2, ensure_ascii=False)}")

    try:
        response = requests.post(f"{BASE_URL}/find/instassociation", json=params)
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")

        associations = data.get("info", [])
        print(f"\n找到 {len(associations)} 条关联记录:")
        for assoc in associations:
            print(f"  - ID: {assoc.get('id')}")
            print(f"    源: {assoc.get('bk_obj_id')}/{assoc.get('bk_inst_id')}")
            print(f"    目标: {assoc.get('bk_asst_obj_id')}/{assoc.get('bk_asst_inst_id')}")
            print(f"    关联类型: {assoc.get('bk_obj_asst_id')}")
            print()

        return associations
    except Exception as e:
        print(f"错误: {e}")
        return []

def test_delete_association(assoc_id):
    """测试删除关联"""
    print("\n" + "=" * 60)
    print(f"测试删除关联 (ID={assoc_id})")
    print("=" * 60)

    try:
        response = requests.delete(f"{BASE_URL}/delete/instassociation/bk_slb/{assoc_id}")
        print(f"状态码: {response.status_code}")
        print(f"响应数据: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"错误: {e}")
        return None

def test_query_all_associations():
    """查询所有关联数据"""
    print("\n" + "=" * 60)
    print("查询所有关联数据")
    print("=" * 60)

    try:
        response = requests.post(f"{BASE_URL}/find/instassociation", json={})
        print(f"状态码: {response.status_code}")
        data = response.json()
        associations = data.get("info", [])
        print(f"总共找到 {len(associations)} 条关联记录")

        # 统计 SLB 相关的关联
        slb_associations = [a for a in associations if a.get('bk_obj_id') == 'bk_slb' or a.get('bk_asst_obj_id') == 'bk_slb']
        print(f"其中 SLB 相关关联: {len(slb_associations)} 条")

        return associations
    except Exception as e:
        print(f"错误: {e}")
        return []

if __name__ == "__main__":
    # 1. 查询现有关联
    print("\n步骤1: 查询 SLB 实例 18 的现有关联")
    existing = test_find_association(inst_id=18)

    # 2. 测试创建新关联
    print("\n步骤2: 创建新的关联 (SLB 18 -> SLB Service 1)")
    result = test_create_association()

    # 3. 再次查询验证
    print("\n步骤3: 验证关联是否创建成功")
    test_find_association(inst_id=18, asst_inst_id=1)

    # 4. 如果创建成功，测试删除
    if result and result.get("id"):
        print("\n步骤4: 删除测试创建的关联")
        test_delete_association(result["id"])

        # 5. 验证删除
        print("\n步骤5: 验证删除是否成功")
        test_find_association(inst_id=18, asst_inst_id=1)

    # 6. 查询所有关联数据
    test_query_all_associations()
