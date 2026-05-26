#!/usr/bin/env python3
"""
综合诊断报告：前后端数据流分析
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def generate_diagnostic_report():
    print("=" * 80)
    print("综合诊断报告：前后端数据流分析")
    print("=" * 80)
    
    print("\n【1. 后端 API 验证】")
    print("-" * 80)
    
    # 1.1 创建关联
    print("\n1.1 创建关联 API")
    params = {
        "bk_obj_id": "bk_slb",
        "bk_inst_id": 19,
        "bk_asst_obj_id": "bk_slb_server",
        "bk_asst_inst_id": 3,
        "bk_obj_asst_id": "bk_slb_to_bk_slb_server",
        "bk_relation_type_id": "to"
    }
    
    print(f"创建参数: {json.dumps(params, indent=2, ensure_ascii=False)}")
    
    resp = requests.post(f"{BASE_URL}/create/instassociation", json=params)
    result = resp.json()
    print(f"响应: {result}")
    
    if result.get('result'):
        print("✅ 创建成功")
        new_id = result['id']
    else:
        print("❌ 创建失败")
        return
    
    # 1.2 查询关联
    print("\n1.2 查询关联 API")
    query_params = {
        "bk_obj_id": "bk_slb",
        "condition": {
            "bk_inst_id": 19,
            "bk_obj_asst_id": "bk_slb_to_bk_slb_server"
        }
    }
    
    print(f"查询参数: {json.dumps(query_params, indent=2, ensure_ascii=False)}")
    
    resp = requests.post(f"{BASE_URL}/find/instassociation", json=query_params)
    data = resp.json()
    assocs = data.get('info', [])
    
    print(f"查询结果: {len(assocs)} 条记录")
    
    found = [a for a in assocs if a['id'] == new_id]
    if found:
        print(f"✅ 找到新创建的关联 ID={new_id}")
        print(f"   关联详情:")
        for key, value in found[0].items():
            print(f"     - {key}: {value} (类型: {type(value).__name__})")
    else:
        print(f"❌ 未找到新创建的关联 ID={new_id}")
    
    print("\n【2. 前端查询条件分析】")
    print("-" * 80)
    
    print("\n2.1 前端 getExistInstAssociation 的查询参数应该是什么？")
    
    # 模拟前端查询
    print("\n场景：SLB 实例 19，选择 'slb服务' 关联类型")
    print("   - this.objId = 'bk_slb'")
    print("   - this.instId = 19")
    print("   - this.currentOption.bk_obj_id = 'bk_slb'")
    print("   - this.currentOption.bk_obj_asst_id = 'bk_slb_to_bk_slb_server'")
    
    isSource = True
    frontend_params = {
        "bk_obj_id": "bk_slb" if isSource else None,
        "condition": {
            "bk_inst_id": 19 if isSource else None,
            "bk_asst_inst_id": 19 if not isSource else None,
            "bk_obj_asst_id": "bk_slb_to_bk_slb_server"
        }
    }
    
    if not frontend_params["bk_obj_id"]:
        del frontend_params["bk_obj_id"]
    
    # 移除 None 值
    frontend_params["condition"] = {k: v for k, v in frontend_params["condition"].items() if v is not None}
    
    print(f"\n前端查询参数:")
    print(json.dumps(frontend_params, indent=2, ensure_ascii=False))
    
    # 2.2 验证查询是否能找到数据
    print("\n2.2 使用前端查询参数验证")
    
    resp = requests.post(f"{BASE_URL}/find/instassociation", json=frontend_params)
    data = resp.json()
    assocs = data.get('info', [])
    
    print(f"查询结果: {len(assocs)} 条记录")
    
    found = [a for a in assocs if a['id'] == new_id]
    if found:
        print(f"✅ 前端查询参数正确，能找到新创建的关联")
    else:
        print(f"❌ 前端查询参数有问题，无法找到新创建的关联")
        print(f"   期望 ID={new_id}，但查询返回的记录 ID 为: {[a['id'] for a in assocs]}")
    
    print("\n【3. 数据类型分析】")
    print("-" * 80)
    
    print("\n3.1 检查数据库中字段的类型")
    
    if assocs:
        sample = assocs[0]
        print(f"   bk_inst_id: {sample['bk_inst_id']} (类型: {type(sample['bk_inst_id']).__name__})")
        print(f"   bk_asst_inst_id: {sample['bk_asst_inst_id']} (类型: {type(sample['bk_asst_inst_id']).__name__})")
        print(f"   bk_obj_asst_id: {sample['bk_obj_asst_id']} (类型: {type(sample['bk_obj_asst_id']).__name__})")
    
    print("\n3.2 前端 JavaScript 中的 Number() 转换")
    print("   前端使用 Number() 进行类型转换:")
    print("   - Number('19') =", Number('19'))
    print("   - Number('3') =", Number('3'))
    print("   - Number(exist.bk_asst_inst_id) 应该等于 Number('3')")
    
    print("\n【4. 结论】")
    print("=" * 80)
    
    if found:
        print("✅ 后端 API 正常")
        print("✅ 数据库数据正确")
        print("✅ 查询参数匹配")
        print("\n问题可能在于:")
        print("  1. 前端接收到的 API 响应格式与预期不符")
        print("  2. 前端的状态更新没有触发 UI 重新渲染")
        print("  3. 前端的 bk_obj_asst_id 与数据库不匹配")
    else:
        print("❌ 后端查询参数有问题")
        print("❌ 需要调整前端查询参数")

if __name__ == "__main__":
    generate_diagnostic_report()
