#!/usr/bin/env python3
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.config.settings import get_config

config = get_config('development')
app = create_app(config)

print("=== 所有注册的路由 ===")
for rule in app.url_map.iter_rules():
    methods = ', '.join(rule.methods - {'HEAD', 'OPTIONS'})
    print(f"{rule.rule} [{methods}]")

print("\n=== 测试路由匹配 ===")
with app.test_request_context('/api/v1/models/bk_slb/attributes'):
    from flask import request
    print(f"请求路径: {request.path}")
    try:
        adapter = app.create_url_adapter(request)
        match = adapter.match()
        print(f"匹配成功: {match}")
    except Exception as e:
        print(f"匹配失败: {type(e).__name__}: {e}")
