#!/usr/bin/env python3
import json
from pathlib import Path

# 测试路径解析
file_path = Path(__file__)
print(f"Current file: {file_path}")
project_root = file_path.parent.parent.parent
print(f"Project root: {project_root}")
ui_project = project_root.parent / "cmdb_ui_lite" / "src" / "assets" / "api"
print(f"UI project path: {ui_project}")
print(f"UI project exists: {ui_project.exists()}")

index_path = ui_project / "index.json"
print(f"Index file exists: {index_path.exists()}")

# 检查属性文件
model_ids = ['bk_switch', 'bk_host', 'bk_slb', 'bk_slb_server', 'bk_slb_listener']
for model_id in model_ids:
    attr_path = ui_project / "attributes" / f"{model_id}.json"
    print(f"Attribute file {model_id} exists: {attr_path.exists()}")
    if attr_path.exists():
        with open(attr_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"  - Attributes count: {len(data.get('info', []))}")
