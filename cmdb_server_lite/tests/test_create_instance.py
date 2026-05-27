#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8000"

def test_create_instance():
    """测试创建实例API"""
    
    print("=== 测试创建实例API ===")
    
    # 先获取模型属性定义
    model_id = "bk_slb"
    
    print(f"\n1. 尝试为 {model_id} 创建实例")
    
    # 准备测试数据 - 使用实际的属性字段
    test_data = {
        "data": {
            "bk_slb_name": "测试SLB-API-001",
            "bk_vendor": "tencent",
            "bk_region": "ap-guangzhou",
            "bk_cloud_id": 0,
            "bk_status": "normal",
            "bk_outer_ip": "119.29.29.99",
            "bk_inner_ip": "10.0.0.99",
            "bk_pay_type": 1,
            "bk_biz_id": 2,
            "bk_host_id": 999
        }
    }
    
    try:
        print(f"\n请求数据: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
        
        response = requests.post(
            f"{BASE_URL}/api/models/{model_id}/instances",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应内容: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("\n✅ 创建成功!")
                instance_id = result.get("data", {}).get("id")
                print(f"   实例ID: {instance_id}")
                return True
            else:
                print(f"\n❌ 创建失败: {result.get('message')}")
                return False
        else:
            print(f"\n❌ 请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ 请求异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_check_associations():
    """测试检查关联关系API"""
    print("\n\n=== 测试检查关联关系API ===")
    
    model_id = "bk_slb"
    
    test_data = {
        "ids": [1]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/models/{model_id}/instances/check-associations",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            print("✅ 检查关联关系API正常!")
            return True
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("开始测试新增实例功能...\n")
    
    # 先测试检查关联
    test_check_associations()
    
    # 测试创建实例
    success = test_create_instance()
    
    if success:
        print("\n🎉 所有测试完成! API功能正常!")
    else:
        print("\n⚠️ 测试完成，但有部分失败，请检查!")
