#!/usr/bin/env python3

import duckdb

# 连接数据库
conn = duckdb.connect('/workspace/bk-cmdb/cmdb_server_lite/cmdb.duckdb')

# 查看主机表结构
print("=" * 60)
print("主机表 (cc_ObjectBase_0_pub_bk_host) 结构:")
print("=" * 60)
result = conn.execute("PRAGMA table_info('cc_ObjectBase_0_pub_bk_host')").fetchall()
for row in result:
    print(f"  {row[1]}: {row[2]} (nullable={row[3]})")

# 查看交换机表结构
print("\n" + "=" * 60)
print("交换机表 (cc_ObjectBase_0_pub_bk_switch) 结构:")
print("=" * 60)
result = conn.execute("PRAGMA table_info('cc_ObjectBase_0_pub_bk_switch')").fetchall()
for row in result:
    print(f"  {row[1]}: {row[2]} (nullable={row[3]})")

# 查看属性表中关于系统字段的定义
print("\n" + "=" * 60)
print("属性表 (cc_ObjAttDes) 中系统字段的定义:")
print("=" * 60)
system_fields = ['create_time', 'last_time', 'bk_created_by', 'bk_created_at', 
                 'bk_updated_by', 'bk_updated_at', 'creator', 'modifier', 
                 'created_at', 'updated_at']
for field in system_fields:
    result = conn.execute(f"SELECT bk_property_id, bk_property_name, isreadonly, editable, bk_ishidden, bk_isapi, bk_issystem FROM cc_ObjAttDes WHERE bk_property_id = '{field}'").fetchall()
    if result:
        print(f"\n  {field}:")
        for row in result:
            print(f"    字段名: {row[0]}, 显示名: {row[1]}")
            print(f"    isreadonly: {row[2]}, editable: {row[3]}, bk_ishidden: {row[4]}")
            print(f"    bk_isapi: {row[5]}, bk_issystem: {row[6]}")
    else:
        print(f"\n  {field}: 未在属性表中找到定义")

conn.close()
