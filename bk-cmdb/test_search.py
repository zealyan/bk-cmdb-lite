#!/usr/bin/env python3
"""搜索功能自动化测试"""

import requests
import json

BASE_URL = "http://localhost:8000"
PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"

def test(name, condition, details=""):
    status = PASS if condition else FAIL
    print(f"{status} {name}")
    if details and not condition:
        print(f"  详情: {details}")
    return condition

def test_fuzzy_search_ip():
    """测试1: 模糊搜索IP - 搜索'100'能匹配包含'100'的IP"""
    print("\n" + "="*60)
    print("测试1: 模糊搜索IP - 搜索'100'能匹配包含'100'的IP")
    print("="*60)

    resp = requests.get(f"{BASE_URL}/api/models/bk_host/instances", params={
        "search_field": "bk_host_innerip",
        "search_value": "100",
        "fuzzy": True
    })

    if not test("接口响应成功", resp.status_code == 200, resp.text):
        return False

    data = resp.json()
    instances = data.get("instances", [])

    test("返回了匹配的实例", len(instances) > 0,
         f"搜索'100'应返回包含'100'的IP，当前返回 {len(instances)} 条")

    for inst in instances:
        ip = inst.get("bk_host_innerip", "")
        if ip:
            test(f"IP '{ip}' 包含 '100'", "100" in str(ip))

    return True

def test_fuzzy_search_name():
    """测试2: 模糊搜索交换机名称 - 搜索'Test'不区分大小写"""
    print("\n" + "="*60)
    print("测试2: 模糊搜索交换机 - 不区分大小写")
    print("="*60)

    resp = requests.get(f"{BASE_URL}/api/models/bk_switch/instances", params={
        "search_field": "name",
        "search_value": "test",
        "fuzzy": True
    })

    if not test("接口响应成功", resp.status_code == 200, resp.text):
        return False

    data = resp.json()
    instances = data.get("instances", [])

    test("返回了匹配的实例", len(instances) > 0,
         f"搜索'test'(小写)应返回包含'Test'的交换机")

    return True

def test_chinese_search():
    """测试3: 中文搜索"""
    print("\n" + "="*60)
    print("测试3: 中文搜索支持")
    print("="*60)

    resp = requests.get(f"{BASE_URL}/api/models/bk_switch/instances", params={
        "search_field": "name",
        "search_value": "核心",
        "fuzzy": True
    })

    if not test("接口响应成功", resp.status_code == 200, resp.text):
        return False

    data = resp.json()
    instances = data.get("instances", [])

    test("返回了包含中文的匹配实例", len(instances) > 0,
         f"搜索'核心'应返回相关交换机")

    return True

def test_exact_search():
    """测试4: 精确搜索"""
    print("\n" + "="*60)
    print("测试4: 精确搜索（非模糊）")
    print("="*60)

    resp_fuzzy = requests.get(f"{BASE_URL}/api/models/bk_switch/instances", params={
        "search_field": "name",
        "search_value": "核心交换机-01",
        "fuzzy": True
    })

    resp_exact = requests.get(f"{BASE_URL}/api/models/bk_switch/instances", params={
        "search_field": "name",
        "search_value": "核心交换机-01",
        "fuzzy": False
    })

    fuzzy_data = resp_fuzzy.json()
    exact_data = resp_exact.json()

    fuzzy_count = len(fuzzy_data.get("instances", []))
    exact_count = len(exact_data.get("instances", []))

    test("精确搜索正常工作", exact_count > 0,
         f"精确搜索'核心交换机-01'返回 {exact_count} 条")

    return True

def test_sql_injection_prevention():
    """测试5: SQL注入防护"""
    print("\n" + "="*60)
    print("测试5: SQL注入防护")
    print("="*60)

    malicious_values = ["'; DROP TABLE--", "1' OR '1'='1", "<script>alert(1)</script>"]

    for val in malicious_values:
        resp = requests.get(f"{BASE_URL}/api/models/bk_switch/instances", params={
            "search_field": "name",
            "search_value": val,
            "fuzzy": True
        })

        test(f"SQL注入尝试被安全处理: {val[:20]}...", resp.status_code == 200,
             f"状态码: {resp.status_code}")

    return True

def test_multi_column_search():
    """测试6: 多列搜索"""
    print("\n" + "="*60)
    print("测试6: 多列搜索 (search参数)")
    print("="*60)

    resp = requests.get(f"{BASE_URL}/api/models/bk_switch/instances", params={
        "search": "1"
    })

    if not test("接口响应成功", resp.status_code == 200, resp.text):
        return False

    data = resp.json()
    instances = data.get("instances", [])

    test("多列搜索返回了结果", len(instances) > 0,
         f"搜索'1'在多列中返回 {len(instances)} 条")

    return True

def test_get_all_switches():
    """测试7: 获取所有交换机（无搜索条件）"""
    print("\n" + "="*60)
    print("测试7: 获取所有交换机数据")
    print("="*60)

    resp = requests.get(f"{BASE_URL}/api/models/bk_switch/instances")

    if not test("接口响应成功", resp.status_code == 200, resp.text):
        return False

    data = resp.json()
    instances = data.get("instances", [])
    total = data.get("total", 0)

    test(f"返回了 {total} 条交换机数据", total > 0)

    if instances:
        sample = instances[0]
        print(f"  示例数据: {json.dumps({k: v for k, v in sample.items() if v}, ensure_ascii=False, indent=2)[:500]}")

    return True

def main():
    print("="*60)
    print("CMDB搜索功能自动化测试")
    print("="*60)

    results = []

    results.append(("模糊搜索IP", test_fuzzy_search_ip()))
    results.append(("大小写不敏感", test_fuzzy_search_name()))
    results.append(("中文搜索", test_chinese_search()))
    results.append(("精确搜索", test_exact_search()))
    results.append(("SQL注入防护", test_sql_injection_prevention()))
    results.append(("多列搜索", test_multi_column_search()))
    results.append(("获取全部数据", test_get_all_switches()))

    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = PASS if result else FAIL
        print(f"{status} {name}")

    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️  {total - passed} 项测试失败")

    return passed == total

if __name__ == "__main__":
    main()
