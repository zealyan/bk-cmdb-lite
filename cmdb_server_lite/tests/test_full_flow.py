#!/usr/bin/env python3
"""
测试完整的前端到后端的数据流程
模拟前端 createAssociation 方法的参数
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_frontend_flow():
    print("=" * 80)
    print("模拟前端 createAssociation 完整流程")
    print("=" * 80)
    
    # 场景：SLB 实例 18 关联到 SLB Server ID 2
    
    # 1. 首先查询 SLB 18 当前的关联
    print("\n步骤1: 查询 SLB 实例 18 的当前关联")
    print("-" * 80)
    
    query_params = {
        "bk_obj_id": "bk_slb",
        "condition": {
            "bk_inst_id": 18,
            "bk_obj_asst_id": "bk_slb_to_bk_slb_server"
        }
    }
    
    print(f"查询参数: {json.dumps(query_params, indent=2, ensure_ascii=False)}")
    
    resp = requests.post(f"{BASE_URL}/find/instassociation", json=query_params)
    print(f"响应状态: {resp.status_code}")
    current_assocs = resp.json()
    print(f"当前关联数: {len(current_assocs.get('info', []))}")
    for a in current_assocs.get('info', []):
        print(f"  - ID: {a['id']}, 目标: {a['bk_asst_obj_id']}/{a['bk_asst_inst_id']}")
    
    # 2. 获取模型关联信息
    print("\n步骤2: 获取模型关联信息")
    print("-" * 80)
    
    obj_assoc_resp = requests.post(f"{BASE_URL}/find/objectassociation", json={})
    obj_assocs = obj_assoc_resp.json()
    
    slb_to_server = None
    for obj in obj_assocs:
        if obj['bk_obj_id'] == 'bk_slb' and obj['target_obj_id'] == 'bk_slb_server':
            slb_to_server = obj
            break
    
    if not slb_to_server:
        print("错误: 找不到 SLB 到 SLB Server 的关联定义")
        return
    
    print(f"找到关联定义:")
    print(f"  bk_obj_id: {slb_to_server['bk_obj_id']}")
    print(f"  target_obj_id: {slb_to_server['target_obj_id']}")
    print(f"  bk_obj_asst_id: {slb_to_server['bk_obj_asst_id']}")
    print(f"  bk_asst_id: {slb_to_server['bk_asst_id']}")
    
    # 3. 模拟前端 createAssociation 的参数构建
    print("\n步骤3: 模拟前端 createAssociation 参数")
    print("-" * 80)
    
    # 假设 SLB 实例 18 是源对象（isSource = True）
    # currentOption.bk_obj_id = 'bk_slb'
    # this.objId = 'bk_slb'
    # this.instId = 18
    # this.currentAsstObj = 'bk_slb_server'
    
    isSource = True
    objId = 'bk_slb'
    instId = 18
    currentAsstObj = 'bk_slb_server'
    
    print(f"isSource: {isSource}")
    print(f"objId: {objId}")
    print(f"instId: {instId}")
    print(f"currentAsstObj: {currentAsstObj}")
    
    # 前端构建的参数
    params = {
        'bk_obj_id': objId if isSource else currentAsstObj,
        'bk_inst_id': instId if isSource else 2,  # 假设关联到 ID=2 的 SLB Server
        'bk_asst_obj_id': currentAsstObj if isSource else objId,
        'bk_asst_inst_id': 2 if isSource else instId,
        'bk_obj_asst_id': slb_to_server['bk_obj_asst_id'],
        'bk_relation_type_id': slb_to_server['bk_asst_id']
    }
    
    print(f"\n前端构建的参数:")
    print(f"  bk_obj_id: {params['bk_obj_id']} (源模型)")
    print(f"  bk_inst_id: {params['bk_inst_id']} (源实例)")
    print(f"  bk_asst_obj_id: {params['bk_asst_obj_id']} (目标模型)")
    print(f"  bk_asst_inst_id: {params['bk_asst_inst_id']} (目标实例)")
    print(f"  bk_obj_asst_id: {params['bk_obj_asst_id']} (模型关联)")
    print(f"  bk_relation_type_id: {params['bk_relation_type_id']} (关联类型)")
    
    # 4. 创建关联
    print("\n步骤4: 创建关联")
    print("-" * 80)
    
    create_resp = requests.post(f"{BASE_URL}/create/instassociation", json=params)
    print(f"创建响应状态: {create_resp.status_code}")
    print(f"创建响应: {create_resp.json()}")
    
    # 5. 验证创建结果
    print("\n步骤5: 验证创建结果")
    print("-" * 80)
    
    verify_resp = requests.post(f"{BASE_URL}/find/instassociation", json=query_params)
    verify_data = verify_resp.json()
    verify_assocs = verify_data.get('info', [])
    
    print(f"现在有 {len(verify_assocs)} 条关联:")
    for a in verify_assocs:
        print(f"  - ID: {a['id']}, 目标: {a['bk_asst_obj_id']}/{a['bk_asst_inst_id']}")
    
    # 检查新创建的关联
    new_assoc = [a for a in verify_assocs if a['bk_asst_inst_id'] == 2]
    if new_assoc:
        print(f"\n✅ 创建成功！SLB 18 与 SLB Server 2 的关联已创建")
        print(f"   关联 ID: {new_assoc[0]['id']}")
    else:
        print(f"\n❌ 创建失败！SLB 18 与 SLB Server 2 的关联未找到")

if __name__ == "__main__":
    test_frontend_flow()
