#!/usr/bin/env python3
"""检查user_custom表数据"""

import duckdb
import json
import sys
import os

db_path = '/workspace/bk-cmdb/cmdb_server_lite/cmdb.duckdb'

if not os.path.exists(db_path):
    print(f"Database file not found: {db_path}")
    sys.exit(1)

try:
    conn = duckdb.connect(db_path, read_only=True)
    
    # 检查所有表
    print("=" * 80)
    print("1. 数据库中的所有表")
    print("=" * 80)
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]
    print(f"Table names: {table_names}")
    
    # 检查user_custom表结构
    print("\n" + "=" * 80)
    print("2. user_custom表结构")
    print("=" * 80)
    try:
        columns = conn.execute("DESCRIBE user_custom").fetchall()
        print("Column structure:")
        for col in columns:
            print(f"  {col[0]} ({col[1]})")
    except Exception as e:
        print(f"Error: user_custom table doesn't exist or can't be read: {e}")
    
    # 检查user_custom表数据
    print("\n" + "=" * 80)
    print("3. user_custom表数据")
    print("=" * 80)
    try:
        data = conn.execute("SELECT * FROM user_custom").fetchall()
        print(f"Total rows: {len(data)}")
        if data:
            cols = conn.execute("SELECT * FROM user_custom LIMIT 0").description
            col_names = [c[0] for c in cols]
            print("\nRows:")
            for row in data:
                row_dict = dict(zip(col_names, row))
                print(f"\n  - {row_dict}")
                if row_dict.get('config_value'):
                    try:
                        parsed = json.loads(row_dict['config_value'])
                        print(f"    Parsed config_value: {parsed}")
                    except Exception:
                        pass
    except Exception as e:
        print(f"Error reading user_custom: {e}")
    
    # 检查users表
    print("\n" + "=" * 80)
    print("4. users表数据")
    print("=" * 80)
    try:
        users = conn.execute("SELECT * FROM users").fetchall()
        print(f"Total users: {len(users)}")
        if users:
            cols = conn.execute("SELECT * FROM users LIMIT 0").description
            col_names = [c[0] for c in cols]
            for user in users:
                print(f"  - {dict(zip(col_names, user))}")
    except Exception as e:
        print(f"Error reading users: {e}")
    
    conn.close()
    print("\n" + "=" * 80)
    print("检查完成")
    print("=" * 80)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
