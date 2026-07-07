#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.service.model_service import ModelService
import json

print("测试 ModelService.get_model_attributes('bk_switch')...")

try:
    attributes = ModelService.get_model_attributes('bk_switch')
    print(f"返回了 {len(attributes)} 个属性")
    print("\n=== 属性详情 ===")
    for attr in attributes:
        print(f"\n{attr['bk_property_id']} ({attr['bk_property_name']}):")
        print(f"  bk_isapi: {attr.get('bk_isapi')}")
        print(f"  bk_issystem: {attr.get('bk_issystem')}")
        print(f"  editable: {attr.get('editable')}")
        print(f"  isreadonly: {attr.get('isreadonly')}")
        print(f"  bk_ishidden: {attr.get('bk_ishidden')}")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
