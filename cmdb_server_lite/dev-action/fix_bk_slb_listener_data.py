#!/usr/bin/env python3
"""修复 bk_slb_listener 数据中的双重编码问题"""
import json
import os

input_file = '/workspace/cmdb_ui_lite/src/assets/api/models/instances/bk_slb_listener.json'
output_file = '/workspace/cmdb_ui_lite/src/assets/api/models/instances/bk_slb_listener.json'

print(f"读取文件: {input_file}")
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

instances = data.get('info', [])
updated_count = 0

for inst in instances:
    # 修复 bk_domains
    if 'bk_domains' in inst:
        domains = inst['bk_domains']
        if isinstance(domains, str) and domains.strip().startswith('['):
            try:
                parsed = json.loads(domains)
                inst['bk_domains'] = parsed
                updated_count += 1
            except Exception:
                pass
    
    # 修复 bk_cert_ids
    if 'bk_cert_ids' in inst:
        certs = inst['bk_cert_ids']
        if isinstance(certs, str) and certs.strip().startswith('['):
            try:
                parsed = json.loads(certs)
                inst['bk_cert_ids'] = parsed
                updated_count += 1
            except Exception:
                pass

data['info'] = instances

print(f"写入文件: {output_file}")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"更新了 {updated_count} 个字段")
