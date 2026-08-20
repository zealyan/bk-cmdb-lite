#!/usr/bin/env python3
"""
测试后端 API 返回格式
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_api_response():
    print("=" * 80)
    print("测试后端 API 返回格式")
    print("=" * 80)
    
    # 查询关联
    params = {
        "bk_obj_id": "bk_slb",
        "condition": {
            "bk_inst_id": 1
        }
    }
    
    print("\n查询参数:")
    print(json.dumps(params, indent=2, ensure_ascii=False))
    
    print("\n发送 POST 请求到 /find/instassociation")
    resp = requests.post(f"{BASE_URL}/find/instassociation", json=params)
    
    print(f"\n响应状态码: {resp.status_code}")
    print(f"响应头 Content-Type: {resp.headers.get('Content-Type')}")
    
    print("\n原始响应文本（前500字符）:")
    print(resp.text[:500])
    
    print("\n解析后的 JSON:")
    data = resp.json()
    print(f"JSON 类型: {type(data)}")
    print(f"JSON 内容: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
    
    print("\n验证关键字段:")
    if isinstance(data, dict):
        print(f"  - data 是否有 'info' 字段: {'info' in data}")
        print(f"  - data 是否有 'data' 字段: {'data' in data}")
        print(f"  - info 是否为数组: {isinstance(data.get('info'), list) if 'info' in data else 'N/A'}")
        if 'info' in data:
            print(f"  - info 长度: {len(data['info'])}")
            if data['info']:
                print(f"  - 第一条记录的字段: {list(data['info'][0].keys())}")
    elif isinstance(data, list):
        print(f"  - data 是数组，长度: {len(data)}")
        if data:
            print(f"  - 第一条记录的字段: {list(data[0].keys())}")

if __name__ == "__main__":
    test_api_response()
