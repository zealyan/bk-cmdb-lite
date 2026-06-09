#!/usr/bin/env python3
import json

# 处理 bk_slb_server 实例数据
with open('/workspace/cmdb_ui_lite/src/assets/api/models/instances/bk_slb_server.json', 'r', encoding='utf-8') as f:
    servers = json.load(f)

# 为每个实例添加 list 类型的字段
for server in servers['info']:
    # 添加后端IP列表（模拟）
    ip = server.get('bk_server_ip', '')
    if ip:
        # 生成一些相关的后端IP
        ip_parts = ip.split('.')
        if len(ip_parts) == 4:
            backend_ips = [
                ip,
                f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{int(ip_parts[3]) + 100}",
                f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{int(ip_parts[3]) + 200}"
            ]
            server['bk_backend_ips'] = json.dumps(backend_ips, ensure_ascii=False)
        else:
            server['bk_backend_ips'] = json.dumps([ip], ensure_ascii=False)
    else:
        server['bk_backend_ips'] = '[]'

    # 添加服务器分组
    server_type = server.get('bk_server_type', '')
    if 'web' in server.get('bk_server_name', '').lower():
        server['bk_server_groups'] = json.dumps(['Web服务器', '负载均衡器'], ensure_ascii=False)
    elif 'api' in server.get('bk_server_name', '').lower():
        server['bk_server_groups'] = json.dumps(['应用服务器', '负载均衡器'], ensure_ascii=False)
    elif 'https' in server.get('bk_server_name', '').lower():
        server['bk_server_groups'] = json.dumps(['Web服务器', '应用服务器', '负载均衡器'], ensure_ascii=False)
    elif 'redis' in server.get('bk_server_name', '').lower():
        server['bk_server_groups'] = json.dumps(['缓存服务器', '负载均衡器'], ensure_ascii=False)
    elif 'db' in server.get('bk_server_name', '').lower():
        server['bk_server_groups'] = json.dumps(['数据库服务器', '负载均衡器'], ensure_ascii=False)
    elif 'video' in server.get('bk_server_name', '').lower():
        server['bk_server_groups'] = json.dumps(['应用服务器', '负载均衡器'], ensure_ascii=False)
    else:
        server['bk_server_groups'] = json.dumps(['负载均衡器'], ensure_ascii=False)

# 保存
with open('/workspace/cmdb_ui_lite/src/assets/api/models/instances/bk_slb_server.json', 'w', encoding='utf-8') as f:
    json.dump(servers, f, ensure_ascii=False, indent=2)

print(f"已更新 {len(servers['info'])} 个 SLB Server 实例")
