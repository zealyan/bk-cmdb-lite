#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app import create_app
import json

app = create_app()

with app.test_client() as client:
    print("Testing API GET /api/v1/models/bk_switch/attributes")
    response = client.get('/api/v1/models/bk_switch/attributes')
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.get_data(as_text=True)
        print(f"\n原始返回: {data}")
        
        try:
            json_data = json.loads(data)
            print(f"\n解析后JSON类型: {type(json_data)}")
            
            if isinstance(json_data, list):
                print(f"\n返回属性数量: {len(json_data)}")
                print("\n--- 属性详情 ---")
                for attr in json_data:
                    if isinstance(attr, dict):
                        print(f"\n{attr.get('bk_property_id')} ({attr.get('bk_property_name')}):")
                        print(f"  bk_isapi: {attr.get('bk_isapi')} (类型: {type(attr.get('bk_isapi'))})")
                        print(f"  bk_issystem: {attr.get('bk_issystem')} (类型: {type(attr.get('bk_issystem'))})")
                        print(f"  editable: {attr.get('editable')} (类型: {type(attr.get('editable'))})")
                        print(f"  isreadonly: {attr.get('isreadonly')} (类型: {type(attr.get('isreadonly'))})")
                        print(f"  bk_ishidden: {attr.get('bk_ishidden')} (类型: {type(attr.get('bk_ishidden'))})")
                        print(f"  bk_property_type: {attr.get('bk_property_type')}")
                    else:
                        print(f"\n非字典属性: {attr}")
            else:
                print(f"\nJSON: {json_data}")
        except Exception as e:
            print(f"\n解析错误: {e}")
