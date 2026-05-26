#!/usr/bin/env python3
"""
API层集成测试脚本
只测试API层，不直接访问数据库，避免DuckDB并发访问问题
"""

import requests
import json

API_BASE = 'http://localhost:8000'

def log(message: str, level: str = 'INFO'):
    """记录测试日志"""
    prefix = {
        'INFO': '📋',
        'PASS': '✅',
        'FAIL': '❌',
        'WARN': '⚠️'
    }
    print(f"{prefix.get(level, '📋')} {message}")

def test_api_health():
    """测试API健康检查"""
    log("测试API健康检查")
    try:
        response = requests.get(f'{API_BASE}/health', timeout=5)
        if response.status_code == 200:
            log(f"  Status: {response.status_code}", 'PASS')
            return True
        else:
            log(f"  Status: {response.status_code}", 'FAIL')
            return False
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        return False

def test_api_models():
    """测试模型API"""
    log("\n测试模型API")

    # 1. 测试获取SLB列表
    log("获取SLB列表")
    try:
        response = requests.get(f'{API_BASE}/api/models/bk_slb/instances', timeout=5)
        data = response.json()
        slb_count = data.get('total', 0)
        log(f"  SLB实例数: {slb_count}", 'PASS' if slb_count > 0 else 'FAIL')
        if slb_count == 0:
            return False
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        return False

    # 2. 测试获取后端服务器列表
    log("获取后端服务器列表")
    try:
        response = requests.get(f'{API_BASE}/api/models/bk_slb_server/instances', timeout=5)
        data = response.json()
        server_count = data.get('total', 0)
        log(f"  后端服务器数: {server_count}", 'PASS' if server_count > 0 else 'FAIL')
        if server_count == 0:
            return False
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        return False

    # 3. 测试获取监听器列表
    log("获取监听器列表")
    try:
        response = requests.get(f'{API_BASE}/api/models/bk_slb_listener/instances', timeout=5)
        data = response.json()
        listener_count = data.get('total', 0)
        log(f"  监听器数: {listener_count}", 'PASS' if listener_count > 0 else 'FAIL')
        if listener_count == 0:
            return False
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        return False

    return True

def test_api_associations():
    """测试关联API"""
    log("\n测试关联API")

    # 1. 测试获取SLB ID=1的关联数据
    log("获取SLB ID=1的关联数据")
    try:
        response = requests.get(f'{API_BASE}/api/instances/1/associations', timeout=5)
        data = response.json()
        assocs = data.get('associations', [])

        api_servers = len([a for a in assocs if a.get('bk_asst_obj_id') == 'bk_slb_server'])
        api_listeners = len([a for a in assocs if a.get('bk_asst_obj_id') == 'bk_slb_listener'])

        log(f"  后端服务器关联: {api_servers}条", 'PASS' if api_servers >= 10 else 'WARN')
        log(f"  监听器关联: {api_listeners}条", 'PASS' if api_listeners >= 10 else 'WARN')

        # 检查关联数据完整性
        if api_servers >= 10 and api_listeners >= 10:
            log("  ✅ 关联数据充足", 'PASS')
            return True
        else:
            log("  ⚠️ 关联数据不足", 'WARN')
            return False
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        return False

def test_api_search():
    """测试搜索功能"""
    log("\n测试搜索功能")

    # 1. 测试按bk_slb_id搜索后端服务器
    log("搜索bk_slb_id=1的后端服务器")
    try:
        response = requests.get(
            f'{API_BASE}/api/models/bk_slb_server/instances',
            params={'search_field': 'bk_slb_id', 'search_value': '1'},
            timeout=5
        )
        data = response.json()
        search_count = data.get('total', 0)
        log(f"  搜索结果: {search_count}条", 'PASS' if search_count >= 10 else 'WARN')
        return True
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')
        return False

def test_api_model_details():
    """测试模型详情API"""
    log("\n测试模型详情API")

    # 1. 测试获取SLB模型信息
    log("获取SLB模型信息")
    try:
        response = requests.get(f'{API_BASE}/api/models/bk_slb', timeout=5)
        if response.status_code == 200:
            log("  Status: 200", 'PASS')
        else:
            log(f"  Status: {response.status_code}", 'FAIL')
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')

    # 2. 测试获取SLB模型属性
    log("获取SLB模型属性")
    try:
        response = requests.get(f'{API_BASE}/api/models/bk_slb/attributes', timeout=5)
        if response.status_code == 200:
            data = response.json()
            attr_count = len(data.get('attributes', []))
            log(f"  属性数: {attr_count}", 'PASS' if attr_count > 0 else 'FAIL')
        else:
            log(f"  Status: {response.status_code}", 'FAIL')
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')

    # 3. 测试获取SLB模型关联
    log("获取SLB模型关联")
    try:
        response = requests.get(f'{API_BASE}/api/models/bk_slb/associations', timeout=5)
        if response.status_code == 200:
            data = response.json()
            assoc_count = len(data.get('associations', []))
            log(f"  关联定义数: {assoc_count}", 'PASS' if assoc_count > 0 else 'WARN')
        else:
            log(f"  Status: {response.status_code}", 'FAIL')
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')

def test_api_instance_detail():
    """测试实例详情API"""
    log("\n测试实例详情API")

    # 1. 测试获取后端服务器详情
    log("获取后端服务器ID=22的详情")
    try:
        response = requests.get(f'{API_BASE}/api/models/bk_slb_server/instances/22', timeout=5)
        if response.status_code == 200:
            data = response.json()
            instance = data.get('instance', {})
            name = instance.get('bk_server_name', 'N/A')
            log(f"  实例名称: {name}", 'PASS')
        else:
            log(f"  Status: {response.status_code}", 'FAIL')
    except Exception as e:
        log(f"  Error: {e}", 'FAIL')

def run_all_tests():
    """运行所有API测试"""
    log("\n" + "="*60)
    log("🚀 开始API层集成测试")
    log("="*60)

    # 测试健康检查
    if not test_api_health():
        log("\n❌ API服务不可用，测试终止", 'FAIL')
        return False

    # 测试模型API
    if not test_api_models():
        log("\n❌ 模型API测试失败", 'FAIL')
        return False

    # 测试关联API
    if not test_api_associations():
        log("\n⚠️ 关联API测试有警告", 'WARN')

    # 测试搜索功能
    test_api_search()

    # 测试模型详情
    test_api_model_details()

    # 测试实例详情
    test_api_instance_detail()

    log("\n" + "="*60)
    log("✅ API层测试完成！")
    log("="*60)
    return True

if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
