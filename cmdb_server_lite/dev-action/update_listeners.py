#!/usr/bin/env python3
import json

# 处理 bk_slb_listener 实例数据
with open('/workspace/cmdb_ui_lite/src/assets/api/models/instances/bk_slb_listener.json', 'r', encoding='utf-8') as f:
    listeners = json.load(f)

# 为每个实例添加 list 类型的字段
for listener in listeners['info']:
    # 添加域名列表
    name = listener.get('bk_listener_name', '')
    if 'https' in name or 'ssl' in name:
        listener['bk_domains'] = json.dumps([
            f"www.example.com",
            f"api.example.com",
            f"cdn.example.com"
        ], ensure_ascii=False)
        # 添加证书ID列表
        port = listener.get('bk_frontend_port', 0)
        listener['bk_cert_ids'] = json.dumps([
            f"cert-{port}-2024",
            f"cert-{port}-2025"
        ], ensure_ascii=False)
    elif 'http' in name:
        listener['bk_domains'] = json.dumps([
            f"www.example.org",
            f"api.example.org"
        ], ensure_ascii=False)
        listener['bk_cert_ids'] = '[]'
    elif 'api' in name:
        listener['bk_domains'] = json.dumps([
            f"api.example.com",
            f"api-staging.example.com"
        ], ensure_ascii=False)
        listener['bk_cert_ids'] = json.dumps([
            f"cert-api-{port}-2024"
        ], ensure_ascii=False) if 'https' in name else '[]'
    elif 'redis' in name:
        listener['bk_domains'] = json.dumps([
            "redis.example.com"
        ], ensure_ascii=False)
        listener['bk_cert_ids'] = '[]'
    elif 'mysql' in name:
        listener['bk_domains'] = json.dumps([
            "mysql.example.com",
            "mysql-ro.example.com"
        ], ensure_ascii=False)
        listener['bk_cert_ids'] = '[]'
    elif 'video' in name or 'rtmp' in name or 'hls' in name or 'flv' in name:
        listener['bk_domains'] = json.dumps([
            "video.example.com",
            "stream.example.com",
            "cdn-stream.example.com"
        ], ensure_ascii=False)
        listener['bk_cert_ids'] = json.dumps([
            "cert-video-2024"
        ], ensure_ascii=False)
    elif 'backup' in name or 'dr' in name:
        listener['bk_domains'] = json.dumps([
            "backup.example.com",
            "dr.example.com"
        ], ensure_ascii=False)
        listener['bk_cert_ids'] = json.dumps([
            f"cert-backup-{port}-2024"
        ], ensure_ascii=False) if 'https' in name else '[]'
    elif 'cdn' in name or 'origin' in name:
        listener['bk_domains'] = json.dumps([
            "origin.example.com",
            "cdn.example.com"
        ], ensure_ascii=False)
        listener['bk_cert_ids'] = '[]'
    else:
        listener['bk_domains'] = json.dumps([
            f"{name}.example.com"
        ], ensure_ascii=False)
        listener['bk_cert_ids'] = '[]'

# 保存
with open('/workspace/cmdb_ui_lite/src/assets/api/models/instances/bk_slb_listener.json', 'w', encoding='utf-8') as f:
    json.dump(listeners, f, ensure_ascii=False, indent=2)

print(f"已更新 {len(listeners['info'])} 个 SLB Listener 实例")
