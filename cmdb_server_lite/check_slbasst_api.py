#!/usr/bin/env python3
"""
通过 API 查询 SLB 实例关联数据
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def query_assoc(inst_id):
    params = {
        "bk_obj_id": "bk_slb",
        "condition": {
            "bk_inst_id": inst_id
        }
    }
    
    response = requests.post(f"{BASE_URL}/find/instassociation", json=params)
    data = response.json()
    return data.get("info", [])

def main():
    print("=" * 80)
    print("通过 API 查询 SLB 实例关联数据")
    print("=" * 80)
    
    # 查询实例 2 的关联
    print("\nSLB 实例 2 的关联:")
    print("-" * 80)
    slb2 = query_assoc(2)
    print(f"找到 {len(slb2)} 条关联:")
    for assoc in slb2:
        print(json.dumps(assoc, indent=2, ensure_ascii=False))
    
    # 查询实例 3 的关联
    print("\nSLB 实例 3 的关联:")
    print("-" * 80)
    slb3 = query_assoc(3)
    print(f"找到 {len(slb3)} 条关联:")
    for assoc in slb3:
        print(json.dumps(assoc, indent=2, ensure_ascii=False))
    
    # 查询所有关联
    print("\n所有关联数据:")
    print("-" * 80)
    all_assoc = requests.post(f"{BASE_URL}/find/instassociation", json={}).json().get("info", [])
    print(f"总共有 {len(all_assoc)} 条关联")
    
    # 按 SLB 实例分组统计
    print("\nSLB 相关关联统计:")
    from collections import defaultdict
    slb_stats = defaultdict(list)
    for assoc in all_assoc:
        if assoc.get("bk_obj_id") == "bk_slb":
            slb_stats[f"SLB {assoc['bk_inst_id']} (source)"].append(assoc)
        if assoc.get("bk_asst_obj_id") == "bk_slb":
            slb_stats[f"SLB {assoc['bk_asst_inst_id']} (target)"].append(assoc)
    
    for key, assocs in sorted(slb_stats.items()):
        print(f"  {key}: {len(assocs)} 条关联")

if __name__ == "__main__":
    main()
