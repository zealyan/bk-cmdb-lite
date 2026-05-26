#!/usr/bin/env python3
import json
import os
import glob

def remove_time_fields(json_file):
    """从属性定义文件中删除 created_at 和 updated_at 字段"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'info' not in data:
            return False
        
        original_len = len(data['info'])
        # 过滤掉 created_at 和 updated_at 字段
        data['info'] = [
            prop for prop in data['info'] 
            if prop.get('bk_property_id') not in ['created_at', 'updated_at']
        ]
        
        if len(data['info']) < original_len:
            # 重新编号 bk_property_index
            for idx, prop in enumerate(data['info']):
                if 'bk_property_index' in prop:
                    prop['bk_property_index'] = idx
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        return False
    except Exception as e:
        print(f"处理文件 {json_file} 时出错: {e}")
        return False

# 处理所有属性文件
attributes_dir = '/workspace/bk-cmdb/cmdb_ui_lite/src/assets/api/models/attributes'
files = glob.glob(f"{attributes_dir}/*.json")

removed_count = 0
for json_file in files:
    if remove_time_fields(json_file):
        print(f"已处理: {os.path.basename(json_file)}")
        removed_count += 1

print(f"\n总共处理了 {removed_count} 个文件")

# 重新编号索引
def renumber_indices(json_file):
    """重新编号 bk_property_index"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'info' not in data:
            return
        
        for idx, prop in enumerate(data['info']):
            if 'bk_property_index' in prop:
                prop['bk_property_index'] = idx
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"重新编号文件 {json_file} 时出错: {e}")

for json_file in files:
    renumber_indices(json_file)

print("所有文件的索引已重新编号")
