#!/usr/bin/env python3
import requests
import json
import time

BASE_URL = "http://localhost:8000"


def test_create_instance_system_fields():
    """测试创建实例时系统字段自动设置"""
    
    print("=== 测试创建实例时系统字段自动设置 ===\n")
    
    model_id = "bk_slb"
    
    # 准备测试数据
    test_data = {
        "data": {
            "bk_slb_name": "测试系统字段-001",
            "bk_vendor": "tencent",
            "bk_region": "ap-guangzhou",
            "bk_cloud_id": 0,
            "bk_status": "normal",
            "bk_outer_ip": "119.29.29.101",
            "bk_inner_ip": "10.0.0.101",
            "bk_pay_type": 1,
            "bk_biz_id": 2,
            "bk_host_id": 1001
        }
    }
    
    try:
        print("1. 创建新实例")
        print(f"请求数据: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
        
        response = requests.post(
            f"{BASE_URL}/api/models/{model_id}/instances",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ 创建成功!")
                instance = result.get("data")
                instance_id = instance.get("id")
                print(f"   实例ID: {instance_id}")
                
                # 检查系统字段
                print("\n2. 检查系统字段:")
                system_fields = ["create_time", "last_time", "bk_created_by", 
                               "bk_created_at", "bk_updated_by", "bk_updated_at",
                               "creator", "modifier", "bk_supplier_account"]
                
                all_fields_present = True
                for field in system_fields:
                    if field in instance:
                        value = instance.get(field)
                        print(f"   ✅ {field}: {value}")
                    else:
                        print(f"   ❌ {field}: 未设置")
                        all_fields_present = False
                
                return instance_id, all_fields_present
            else:
                print(f"❌ 创建失败: {result.get('message')}")
                return None, False
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None, False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, False


def test_update_instance_system_fields(instance_id):
    """测试更新实例时系统字段自动更新"""
    
    print("\n\n=== 测试更新实例时系统字段自动更新 ===\n")
    
    model_id = "bk_slb"
    
    # 先获取当前实例的时间
    print("1. 获取实例更新前的数据")
    get_response = requests.get(f"{BASE_URL}/api/models/{model_id}/instances/{instance_id}")
    before_instance = get_response.json().get("data", {})
    before_time = before_instance.get("last_time")
    print(f"   更新前 last_time: {before_time}")
    print(f"   更新前 bk_updated_at: {before_instance.get('updated_at')}")
    
    # 等待一小段时间，确保时间不同
    time.sleep(1)
    
    # 准备更新数据
    update_data = {
        "bk_slb_name": "测试系统字段-001-更新后"
    }
    
    print("\n2. 更新实例")
    print(f"更新数据: {json.dumps(update_data, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.put(
            f"{BASE_URL}/api/models/{model_id}/instances/{instance_id}",
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ 更新成功!")
                instance = result.get("data")
                
                # 检查系统字段是否更新
                print("\n3. 检查系统字段更新:")
                after_time = instance.get("last_time")
                after_updated_at = instance.get("bk_updated_at")
                after_modifier = instance.get("modifier")
                after_updated_by = instance.get("bk_updated_by")
                
                print(f"   更新后 last_time: {after_time}")
                print(f"   更新后 bk_updated_at: {after_updated_at}")
                print(f"   更新后 modifier: {after_modifier}")
                print(f"   更新后 bk_updated_by: {after_updated_by}")
                
                if after_time != before_time:
                    print("   ✅ last_time 已更新")
                else:
                    print("   ❌ last_time 未更新")
                    
                return True
            else:
                print(f"❌ 更新失败: {result.get('message')}")
                return False
        else:
            print(f"❌ 请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_update_system_fields():
    """测试批量更新时系统字段自动更新"""
    
    print("\n\n=== 测试批量更新时系统字段自动更新 ===\n")
    
    model_id = "bk_slb"
    
    # 先创建多个测试实例
    print("1. 创建两个测试实例")
    instance_ids = []
    
    for i in range(2):
        test_data = {
            "data": {
                "bk_slb_name": f"批量更新测试-{i+1}",
                "bk_vendor": "tencent",
                "bk_region": "ap-guangzhou",
                "bk_cloud_id": 0,
                "bk_status": "normal",
                "bk_outer_ip": f"119.29.29.{200+i}",
                "bk_inner_ip": f"10.0.0.{200+i}",
                "bk_pay_type": 1,
                "bk_biz_id": 2,
                "bk_host_id": 2000+i
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/models/{model_id}/instances",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                instance_id = result.get("data", {}).get("id")
                instance_ids.append(instance_id)
                print(f"   ✅ 创建实例 {instance_id}")
    
    if len(instance_ids) < 2:
        print("❌ 无法创建足够的测试实例")
        return False
    
    # 等待一小段时间
    time.sleep(1)
    
    # 获取更新前的时间
    before_times = {}
    for instance_id in instance_ids:
        get_response = requests.get(f"{BASE_URL}/api/models/{model_id}/instances/{instance_id}")
        instance = get_response.json().get("data", {})
        before_times[instance_id] = instance.get("last_time")
    
    # 执行批量更新
    print("\n2. 执行批量更新")
    batch_data = {
        "ids": instance_ids,
        "data": {
            "bk_status": "stop"
        }
    }
    
    response = requests.put(
        f"{BASE_URL}/api/models/{model_id}/instances",
        json=batch_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print(f"✅ 批量更新成功! 更新了 {result.get('updated_count')} 个实例")
            
            # 检查更新后的时间
            print("\n3. 检查批量更新后的时间:")
            all_updated = True
            for instance_id in instance_ids:
                get_response = requests.get(f"{BASE_URL}/api/models/{model_id}/instances/{instance_id}")
                instance = get_response.json().get("data", {})
                after_time = instance.get("last_time")
                before_time = before_times.get(instance_id)
                
                if after_time != before_time:
                    print(f"   实例 {instance_id}: last_time 已更新")
                else:
                    print(f"   实例 {instance_id}: ❌ last_time 未更新")
                    all_updated = False
            
            return all_updated
        else:
            print(f"❌ 批量更新失败: {result.get('message')}")
            return False
    else:
        print(f"❌ 请求失败: {response.status_code}")
        return False


if __name__ == "__main__":
    print("开始测试系统字段自动设置功能...\n")
    
    all_passed = True
    
    # 测试1: 创建实例时系统字段设置
    instance_id, create_success = test_create_instance_system_fields()
    if create_success:
        print("\n✅ 系统字段设置测试通过")
    else:
        print("\n❌ 系统字段设置测试失败")
        all_passed = False
    
    # 测试2: 更新实例时系统字段更新
    if instance_id:
        update_success = test_update_instance_system_fields(instance_id)
        if update_success:
            print("\n✅ 系统字段更新测试通过")
        else:
            print("\n❌ 系统字段更新测试失败")
            all_passed = False
    
    # 测试3: 批量更新时系统字段更新
    batch_success = test_batch_update_system_fields()
    if batch_success:
        print("\n✅ 批量更新系统字段测试通过")
    else:
        print("\n❌ 批量更新系统字段测试失败")
        all_passed = False
    
    if all_passed:
        print("\n🎉 所有系统字段功能测试通过!")
    else:
        print("\n⚠️  有测试失败，请检查!")
