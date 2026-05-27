#!/usr/bin/env python3
"""
将 JSON API 数据文件中的 char 类型统一替换为 singlechar
"""
import os
import json
import glob

# JSON API 数据文件路径
JSON_DIR = os.path.join(os.path.dirname(__file__), 'src', 'assets', 'api', 'models', 'attributes')

def update_file(file_path):
    """更新单个 JSON 文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        updated = False
        # 处理包含 info 字段的 JSON 文件
        if isinstance(data, dict) and 'info' in data:
            attributes = data['info']
        else:
            attributes = data
        
        for attr in attributes:
            if attr.get('bk_property_type') == 'char':
                attr['bk_property_type'] = 'singlechar'
                updated = True
        
        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Updated: {file_path}")
        else:
            print(f"No changes needed: {file_path}")
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def main():
    """主函数"""
    json_files = glob.glob(os.path.join(JSON_DIR, '*.json'))
    print(f"Found {len(json_files)} JSON files to update\n")
    
    for file_path in json_files:
        update_file(file_path)
    
    print("\nDone!")

if __name__ == "__main__":
    main()
