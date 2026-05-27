#!/usr/bin/env python3
import json
import os
import glob

def remove_time_fields_from_instances(json_file):
    """从实例数据文件中删除 created_at 和 updated_at 字段"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'info' not in data:
            return False
        
        modified = False
        for instance in data['info']:
            if 'created_at' in instance:
                del instance['created_at']
                modified = True
            if 'updated_at' in instance:
                del instance['updated_at']
                modified = True
        
        if modified:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        return False
    except Exception as e:
        print(f"处理实例文件 {json_file} 时出错: {e}")
        return False

# 处理所有实例文件
instances_dir = '/workspace/bk-cmdb/cmdb_ui_lite/src/assets/api/models/instances'
files = glob.glob(f"{instances_dir}/*.json")

removed_count = 0
for json_file in files:
    if remove_time_fields_from_instances(json_file):
        print(f"已处理: {os.path.basename(json_file)}")
        removed_count += 1

print(f"\n总共处理了 {removed_count} 个实例文件")
