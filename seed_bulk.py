#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
造数脚本：bk-cmdb-lite 大数据量性能验证
- 主机(host) 补到 10000 条
- 交换机(bk_switch) 补到 10000 条
- 新增 bk_switch -> host 关联定义 (cc_ObjAsst)
- 交换机关联(host) 模拟 5000 条 (双向写入 cc_InstAsst_0_pub_bk_switch / cc_InstAsst_0_pub_host)
"""
import sqlite3, time, random

DB = '/workspace/bk-cmdb-lite/cmdb_server_lite/cmdb_dev.db'
con = sqlite3.connect(DB)
con.execute("PRAGMA busy_timeout=60000")
con.execute("PRAGMA journal_mode=WAL")
cur = con.cursor()

TARGET_HOST = 10000
TARGET_SWITCH = 10000
TARGET_ASSOC = 5000
now = time.strftime('%Y-%m-%d %H:%M:%S')

# ---------------- 1. 主机补到 10000 ----------------
host_cols = ['_id','bk_host_id','bk_host_name','bk_host_innerip','bk_host_outerip','bk_host_inneripv6',
      'bk_host_outeripv6','bk_cloud_id','bk_cloud_inst_id','bk_agent_id','bk_supplier_account',
      'operator','bk_bak_operator','bk_asset_id','bk_sn','bk_comment','bk_service_term','bk_sla',
      'bk_state_name','bk_province_name','bk_isp_name','bk_os_type','bk_os_name','bk_os_version',
      'bk_os_bit','bk_cpu','bk_cpu_mhz','bk_cpu_module','bk_mem','bk_disk','bk_mac','bk_outer_mac',
      'import_from','create_time','last_time','creator','modifier']
host_sql = f"INSERT INTO cc_HostBase ({','.join(host_cols)}) VALUES ({','.join(['?']*len(host_cols))})"
host_max = cur.execute('SELECT COALESCE(max(bk_host_id),0) FROM cc_HostBase').fetchone()[0]
host_need = max(0, TARGET_HOST - host_max)
host_rows = []
for i in range(host_need):
    hid = host_max + 1 + i
    innerip = f"10.12.{(hid//250)%250}.{hid%250+1}"
    host_rows.append([
        f"host.{hid}", hid, f"host-{hid}", innerip, f"11.22.{hid%250}.{hid%250+1}",
        '', '', 0, f"ins-{hid}", f"agent-{hid}", '0',
        'admin', 'backup_admin', f"ASSET-{hid:06d}", f"SN{hid:08d}",
        f"这是一台用于一万级分页性能验证的主机，编号 {hid}；用于验证大列表冻结、请求取消与 DOM 回收机制。",
        '2024', 'P1', '运行中', '广东', '腾讯云',
        'linux', 'Linux', '3.10.0', '64',
        'Intel Xeon', 2600, f"Xeon-E5-{hid%99}", 16384, 500,
        f"ac:1f:{hid%99:02d}:00:00:01", f"ac:1f:{hid%99:02d}:00:00:02",
        'api', now, now, 'admin', 'admin'
    ])
if host_rows:
    for s in range(0, len(host_rows), 1000):
        cur.executemany(host_sql, host_rows[s:s+1000])
    con.commit()
print(f'[主机] 原有 {host_max} 条, 新增 {host_need} 条 -> 目标 {TARGET_HOST}')

# ---------------- 2. 交换机补到 10000 ----------------
sw_cols = ['_id','id','bk_inst_id','bk_inst_name','bk_supplier_account','bk_obj_id','create_time','last_time',
      'bk_operate_time','name','management_ip','model','vendor','vlan','biz_name','description','asset_id',
      'sn','import_from','bk_cloud_id','bk_host_innerip','bk_host_outerip','os_type','os_version',
      'cpu_model','cpu_module','bk_disk','bk_mem','port_count','up_link','power_type','mac_address',
      'app_id','bk_sla','bk_bakcup','service_category','operator','bk_biz_name','bk_company_id','bk_regions']
sw_sql = f"INSERT INTO cc_ObjectBase_0_pub_bk_switch ({','.join(sw_cols)}) VALUES ({','.join(['?']*len(sw_cols))})"
sw_inst_max = cur.execute('SELECT COALESCE(max(bk_inst_id),0) FROM cc_ObjectBase_0_pub_bk_switch').fetchone()[0]
sw_id_max = cur.execute('SELECT COALESCE(max(id),0) FROM cc_ObjectBase_0_pub_bk_switch').fetchone()[0]
sw_need = max(0, TARGET_SWITCH - sw_inst_max)
sw_rows = []
for i in range(sw_need):
    iid = sw_inst_max + 1 + i
    sid = sw_id_max + 1 + i
    sw_rows.append([
        f"bk_switch.{iid}", sid, iid, f"sw-{iid:05d}", '0', 'bk_switch', now, now, now,
        f"sw-{iid:05d}", f"192.168.{iid%250}.{iid%250+1}", 'H3C S5560', 'H3C', 100, '业务A',
        f"用于一万级分页性能验证的交换机实例编号 {iid}；用于验证大列表冻结与回收机制。", f"AS{iid:06d}", f"SN{iid:08d}",
        'api', 0, f"10.0.{iid%250}.{iid%250+1}", f"20.0.{iid%250}.{iid%250+1}", 'Linux', '3.10',
        'Intel', f"Xeon-{iid%99}", 500, 32768, 48, '10G', 'AC', f"ac:1f:{iid%99:02d}:00:00:01",
        3, 'P1', 'backup', '核心', 'admin', '业务A', 0, '华南'
    ])
if sw_rows:
    for s in range(0, len(sw_rows), 1000):
        cur.executemany(sw_sql, sw_rows[s:s+1000])
    con.commit()
print(f'[交换机] 原有 {sw_inst_max} 条, 新增 {sw_need} 条 -> 目标 {TARGET_SWITCH}')

# ---------------- 3. 新增 bk_switch -> host 关联定义 ----------------
asst_cols = ['_id','id','bk_obj_id','target_obj_id','target_obj_name','bk_asst_id','bk_obj_asst_id',
             'bk_obj_asst_name','mapping','on_delete','creator','modifier','create_time','last_time','bk_supplier_account']
exists = cur.execute("SELECT 1 FROM cc_ObjAsst WHERE bk_obj_asst_id='bk_switch_default_host'").fetchone()
if not exists:
    aid = cur.execute('SELECT COALESCE(max(id),0) FROM cc_ObjAsst').fetchone()[0] + 1
    cur.execute(f"INSERT INTO cc_ObjAsst ({','.join(asst_cols)}) VALUES ({','.join(['?']*len(asst_cols))})",
        [None, aid, 'bk_switch', 'host', '主机', 'default', 'bk_switch_default_host',
         '交换机下挂主机', '1:n', 'none', 'admin', 'admin', now, now, '0'])
    con.commit()
    print(f'[关联定义] 新增 bk_switch->host (bk_obj_asst_id=bk_switch_default_host, id={aid})')
else:
    print('[关联定义] bk_switch_default_host 已存在, 跳过')

# ---------------- 4. 交换机关联 5000 条 (双向) ----------------
OBJ_ASST_ID = 'bk_switch_default_host'
switch_id_max = cur.execute('SELECT COALESCE(max(id),0) FROM cc_InstAsst_0_pub_bk_switch').fetchone()[0]
host_asst_id_max = cur.execute('SELECT COALESCE(max(id),0) FROM cc_InstAsst_0_pub_host').fetchone()[0]

pairs = set()
while len(pairs) < TARGET_ASSOC:
    S = random.randint(1, TARGET_SWITCH)   # 交换机实例 id (1..10000)
    H = random.randint(1, TARGET_HOST)     # 主机实例 id (1..10000)
    pairs.add((S, H))

switch_rows = []
host_rows_asst = []
sid = switch_id_max
hid_a = host_asst_id_max
for (S, H) in pairs:
    sid += 1
    switch_rows.append([None, sid, 'bk_switch', S, 'host', H, OBJ_ASST_ID, 'default', '0'])
    hid_a += 1
    host_rows_asst.append([None, hid_a, 'host', H, 'bk_switch', S, OBJ_ASST_ID, 'default', '0'])

asst_sql = (f"INSERT INTO cc_InstAsst_0_pub_bk_switch "
            f"(_id,id,bk_obj_id,bk_inst_id,bk_asst_obj_id,bk_asst_inst_id,bk_obj_asst_id,bk_relation_type_id,bk_supplier_account) "
            f"VALUES (?,?,?,?,?,?,?,?,?)")
host_asst_sql = (f"INSERT INTO cc_InstAsst_0_pub_host "
                 f"(_id,id,bk_obj_id,bk_inst_id,bk_asst_obj_id,bk_asst_inst_id,bk_obj_asst_id,bk_relation_type_id,bk_supplier_account) "
                 f"VALUES (?,?,?,?,?,?,?,?,?)")
for s in range(0, len(switch_rows), 1000):
    cur.executemany(asst_sql, switch_rows[s:s+1000])
    cur.executemany(host_asst_sql, host_rows_asst[s:s+1000])
con.commit()
print(f'[交换机关联] 生成 {len(switch_rows)} 条 (bk_switch 为源 + host 反向, 共 {len(switch_rows)*2} 行)')

# ---------------- 终态统计 ----------------
print('=== 终态 ===')
print('cc_HostBase:', cur.execute('SELECT count(*) FROM cc_HostBase').fetchone()[0])
print('cc_ObjectBase_0_pub_bk_switch:', cur.execute('SELECT count(*) FROM cc_ObjectBase_0_pub_bk_switch').fetchone()[0])
print('cc_InstAsst_0_pub_bk_switch:', cur.execute('SELECT count(*) FROM cc_InstAsst_0_pub_bk_switch').fetchone()[0])
print('cc_InstAsst_0_pub_host:', cur.execute('SELECT count(*) FROM cc_InstAsst_0_pub_host').fetchone()[0])
con.close()
print('DONE')
