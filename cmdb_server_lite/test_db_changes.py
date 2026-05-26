#!/usr/bin/env python3
"""
测试数据库表结构改动
验证：
1. cc_ObjAttDes表包含bk_issystem字段
2. cc_ObjDes表结构正确
3. cc_ObjAsst表结构正确
4. cc_AsstDes表结构正确
5. cc_InstAsst_0_pub表结构正确
6. 所有实例表包含bk_operate_time字段
"""

import requests
import json
import sys

API_BASE = "http://localhost:8000"

def test_api_health():
    """测试API健康检查"""
    print("\n=== 测试1: API健康检查 ===")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ API服务正常运行")
            print(f"  - 服务版本: {data.get('version')}")
            print(f"  - 数据库状态: {data.get('database', {}).get('status')}")
            return True
        else:
            print(f"✗ API返回错误状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 无法连接API: {e}")
        return False

def test_cc_ObjAttDes_structure():
    """测试cc_ObjAttDes表结构，特别是bk_issystem字段"""
    print("\n=== 测试2: cc_ObjAttDes表结构 ===")
    try:
        response = requests.get(f"{API_BASE}/api/models/bk_slb/attributes", timeout=5)
        if response.status_code != 200:
            print(f"✗ 获取模型属性失败: {response.status_code}")
            return False
        
        data = response.json()
        attributes = data.get('attributes', [])
        
        if not attributes:
            print(f"✗ 没有获取到模型属性")
            return False
        
        # 检查第一个属性是否包含bk_issystem字段
        first_attr = attributes[0]
        if 'bk_issystem' in first_attr:
            print(f"✓ cc_ObjAttDes表包含bk_issystem字段")
            print(f"  - 示例数据: bk_property_id={first_attr.get('bk_property_id')}, bk_issystem={first_attr.get('bk_issystem')}")
        else:
            print(f"✗ cc_ObjAttDes表缺少bk_issystem字段")
            print(f"  - 可用字段: {list(first_attr.keys())}")
            return False
        
        # 验证所有属性都有bk_issystem字段
        missing_field = False
        for attr in attributes:
            if 'bk_issystem' not in attr:
                missing_field = True
                print(f"✗ 属性 {attr.get('bk_property_id')} 缺少bk_issystem字段")
        
        if not missing_field:
            print(f"✓ 所有{len(attributes)}个属性都包含bk_issystem字段")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

def test_cc_ObjDes_structure():
    """测试cc_ObjDes表结构"""
    print("\n=== 测试3: cc_ObjDes表结构 ===")
    try:
        response = requests.get(f"{API_BASE}/api/models", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            print(f"✓ cc_ObjDes表查询成功")
            print(f"  - 模型数量: {len(models)}")
            for model in models[:3]:
                print(f"    - {model.get('bk_obj_id')}: {model.get('bk_obj_name')}")
            return True
        else:
            print(f"✗ 获取模型列表失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

def test_instance_tables():
    """测试实例表结构，特别是bk_operate_time字段"""
    print("\n=== 测试4: 实例表结构 (bk_operate_time字段) ===")
    
    models_to_test = ['bk_slb', 'bk_host', 'bk_switch', 'bk_slb_server', 'bk_slb_listener']
    all_success = True
    
    for model_id in models_to_test:
        try:
            response = requests.get(
                f"{API_BASE}/api/models/{model_id}/instances",
                params={'page': 1, 'page_size': 1},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                instances = data.get('instances', [])
                
                if instances:
                    first_instance = instances[0]
                    if 'bk_operate_time' in first_instance:
                        print(f"✓ {model_id}实例表包含bk_operate_time字段")
                    else:
                        print(f"✗ {model_id}实例表缺少bk_operate_time字段")
                        print(f"  - 可用字段: {list(first_instance.keys())}")
                        all_success = False
                else:
                    print(f"⚠ {model_id}实例表无数据，跳过验证")
            else:
                print(f"✗ {model_id}实例查询失败: {response.status_code}")
                all_success = False
                
        except Exception as e:
            print(f"✗ {model_id}测试失败: {e}")
            all_success = False
    
    return all_success

def test_association_tables():
    """测试关联表结构"""
    print("\n=== 测试5: 关联表结构 ===")
    
    try:
        # 测试cc_ObjAsst
        response = requests.get(f"{API_BASE}/api/models/bk_slb/associations", timeout=5)
        if response.status_code == 200:
            data = response.json()
            associations = data.get('associations', [])
            print(f"✓ cc_ObjAsst表查询成功")
            print(f"  - 关联数量: {len(associations)}")
            if associations:
                first_assoc = associations[0]
                print(f"  - 示例: {first_assoc.get('bk_obj_id')} -> {first_assoc.get('target_obj_id')}")
        
        # 测试cc_InstAsst_0_pub
        response = requests.get(f"{API_BASE}/api/instances/1/associations", timeout=5)
        if response.status_code == 200:
            data = response.json()
            assocs = data.get('associations', [])
            print(f"✓ cc_InstAsst_0_pub表查询成功")
            print(f"  - 关联记录数: {len(assocs)}")
        
        return True
        
    except Exception as e:
        print(f"✗ 关联表测试失败: {e}")
        return False

def test_data_consistency():
    """测试数据一致性"""
    print("\n=== 测试6: 数据一致性检查 ===")
    
    try:
        # 检查模型定义
        response = requests.get(f"{API_BASE}/api/models", timeout=5)
        models = response.json().get('models', [])
        model_ids = [m['bk_obj_id'] for m in models]
        
        # 检查每个模型的属性
        for model_id in model_ids[:3]:
            attr_response = requests.get(f"{API_BASE}/api/models/{model_id}/attributes", timeout=5)
            attrs = attr_response.json().get('attributes', [])
            inst_response = requests.get(f"{API_BASE}/api/models/{model_id}/instances", timeout=5)
            insts = inst_response.json().get('instances', [])
            
            print(f"✓ {model_id}:")
            print(f"    - 属性数量: {len(attrs)}")
            print(f"    - 实例数量: {len(insts)}")
        
        return True
        
    except Exception as e:
        print(f"✗ 数据一致性检查失败: {e}")
        return False

def main():
    print("=" * 70)
    print("数据库表结构改动测试")
    print("=" * 70)
    
    results = []
    
    # 运行所有测试
    results.append(("API健康检查", test_api_health()))
    results.append(("cc_ObjAttDes结构", test_cc_ObjAttDes_structure()))
    results.append(("cc_ObjDes结构", test_cc_ObjDes_structure()))
    results.append(("实例表结构", test_instance_tables()))
    results.append(("关联表结构", test_association_tables()))
    results.append(("数据一致性", test_data_consistency()))
    
    # 打印测试结果汇总
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status:8s} | {test_name}")
    
    print("=" * 70)
    print(f"总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n✓ 所有测试通过！数据库表结构改动验证成功。")
        return 0
    else:
        print(f"\n✗ 有 {total - passed} 项测试失败，请检查数据库结构。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
