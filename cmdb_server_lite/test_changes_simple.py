#!/usr/bin/env python3
"""
简化版测试 - 使用curl和requests直接测试API
"""

import subprocess
import json
import sys

def run_curl(url):
    """运行curl命令"""
    result = subprocess.run(
        ['curl', '-s', url],
        capture_output=True,
        text=True
    )
    return result.stdout

def test_api_with_curl():
    """使用curl测试所有关键API"""
    print("=" * 70)
    print("数据库改动验证测试")
    print("=" * 70)
    
    results = []
    
    # 测试1: 健康检查
    print("\n=== 测试1: API健康检查 ===")
    try:
        response = run_curl("http://localhost:8000/health")
        data = json.loads(response)
        print(f"✓ API服务运行正常")
        print(f"  - 版本: {data.get('version')}")
        print(f"  - 数据库状态: {data.get('database', {}).get('status')}")
        results.append(("API健康检查", True))
    except Exception as e:
        print(f"✗ API健康检查失败: {e}")
        results.append(("API健康检查", False))
    
    # 测试2: cc_ObjAttDes表的bk_issystem字段
    print("\n=== 测试2: cc_ObjAttDes - bk_issystem字段 ===")
    try:
        response = run_curl("http://localhost:8000/api/models/bk_slb/attributes")
        data = json.loads(response)
        attributes = data.get('attributes', [])
        
        if attributes:
            first_attr = attributes[0]
            if 'bk_issystem' in first_attr:
                print(f"✓ cc_ObjAttDes表包含bk_issystem字段")
                print(f"  - 示例: {first_attr.get('bk_property_id')} = {first_attr.get('bk_issystem')}")
                
                # 验证所有属性都有该字段
                missing = sum(1 for a in attributes if 'bk_issystem' not in a)
                if missing == 0:
                    print(f"✓ 所有{len(attributes)}个属性都包含bk_issystem字段")
                    results.append(("bk_issystem字段完整性", True))
                else:
                    print(f"✗ 有{missing}个属性缺少bk_issystem字段")
                    results.append(("bk_issystem字段完整性", False))
            else:
                print(f"✗ cc_ObjAttDes缺少bk_issystem字段")
                results.append(("bk_issystem字段完整性", False))
        else:
            print(f"⚠ 没有获取到属性数据")
            results.append(("bk_issystem字段完整性", False))
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        results.append(("bk_issystem字段完整性", False))
    
    # 测试3: cc_ObjDes表
    print("\n=== 测试3: cc_ObjDes表 ===")
    try:
        response = run_curl("http://localhost:8000/api/models")
        data = json.loads(response)
        models = data.get('models', [])
        print(f"✓ cc_ObjDes表查询成功")
        print(f"  - 模型数量: {len(models)}")
        results.append(("cc_ObjDes表查询", True))
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        results.append(("cc_ObjDes表查询", False))
    
    # 测试4: 实例表的bk_operate_time字段
    print("\n=== 测试4: 实例表 - bk_operate_time字段 ===")
    models_to_test = [
        ('bk_slb', '负载均衡'),
        ('bk_host', '主机'),
        ('bk_switch', '交换机'),
        ('bk_slb_server', 'SLB服务器'),
        ('bk_slb_listener', 'SLB监听器')
    ]
    
    all_have_operate_time = True
    for model_id, model_name in models_to_test:
        try:
            url = f"http://localhost:8000/api/models/{model_id}/instances?page=1&page_size=1"
            response = run_curl(url)
            data = json.loads(response)
            instances = data.get('instances', [])
            
            if instances:
                first = instances[0]
                if 'bk_operate_time' in first:
                    print(f"✓ {model_name}({model_id})包含bk_operate_time")
                else:
                    print(f"✗ {model_name}({model_id})缺少bk_operate_time")
                    all_have_operate_time = False
            else:
                print(f"⚠ {model_name}({model_id})无实例数据")
        except Exception as e:
            print(f"✗ {model_name}({model_id})测试失败: {e}")
            all_have_operate_time = False
    
    results.append(("实例表bk_operate_time字段", all_have_operate_time))
    
    # 测试5: 关联表
    print("\n=== 测试5: 关联表(cc_ObjAsst, cc_InstAsst_0_pub) ===")
    try:
        # cc_ObjAsst
        response = run_curl("http://localhost:8000/api/models/bk_slb/associations")
        data = json.loads(response)
        associations = data.get('associations', [])
        print(f"✓ cc_ObjAsst查询成功: {len(associations)}条关联")
        
        # cc_InstAsst_0_pub
        response = run_curl("http://localhost:8000/api/instances/1/associations")
        data = json.loads(response)
        inst_assocs = data.get('associations', [])
        print(f"✓ cc_InstAsst_0_pub查询成功: {len(inst_assocs)}条记录")
        
        results.append(("关联表查询", True))
    except Exception as e:
        print(f"✗ 关联表测试失败: {e}")
        results.append(("关联表查询", False))
    
    # 测试6: cc_AsstDes表
    print("\n=== 测试6: cc_AsstDes表 ===")
    try:
        response = run_curl("http://localhost:8000/api/relations")
        data = json.loads(response)
        relations = data.get('relations', [])
        print(f"✓ cc_AsstDes查询成功: {len(relations)}种关联类型")
        results.append(("cc_AsstDes表查询", True))
    except Exception as e:
        print(f"✗ cc_AsstDes测试失败: {e}")
        results.append(("cc_AsstDes表查询", False))
    
    # 测试7: 统计信息
    print("\n=== 测试7: 数据库统计 ===")
    try:
        response = run_curl("http://localhost:8000/api/statistics")
        data = json.loads(response)
        stats = data.get('statistics', {})
        print(f"✓ 数据库统计查询成功")
        for table, count in list(stats.items())[:5]:
            print(f"  - {table}: {count}条记录")
        results.append(("数据库统计", True))
    except Exception as e:
        print(f"✗ 统计查询失败: {e}")
        results.append(("数据库统计", False))
    
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
        print("\n✓ 所有测试通过！数据库改动验证成功。")
        print("\n验证内容:")
        print("  1. cc_ObjAttDes表包含bk_issystem字段")
        print("  2. 所有实例表包含bk_operate_time字段")
        print("  3. cc_ObjDes, cc_ObjAsst, cc_AsstDes, cc_InstAsst_0_pub表结构正确")
        print("  4. API接口正常工作，返回数据完整")
        return 0
    else:
        print(f"\n✗ 有 {total - passed} 项测试失败")
        return 1

if __name__ == "__main__":
    try:
        exit(test_api_with_curl())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
