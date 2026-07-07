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
        data = response.get_json()
        print(f"\n返回属性数量: {len(data)}")
        print("\n--- 属性详情 ---")
        for attr in data:
            print(f"\n{attr.get('bk_property_id')} ({attr.get('bk_property_name')}):")
            print(f"  bk_isapi: {attr.get('bk_isapi')} (类型: {type(attr.get('bk_isapi'))})")
            print(f"  bk_issystem: {attr.get('bk_issystem')} (类型: {type(attr.get('bk_issystem'))})")
            print(f"  editable: {attr.get('editable')} (类型: {type(attr.get('editable'))})")
            print(f"  isreadonly: {attr.get('isreadonly')} (类型: {type(attr.get('isreadonly'))})")
            print(f"  bk_ishidden: {attr.get('bk_ishidden')} (类型: {type(attr.get('bk_ishidden'))})")
            print(f"  bk_property_type: {attr.get('bk_property_type')}")
