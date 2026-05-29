#!/usr/bin/env python3
"""
数据迁移脚本：从 DuckDB 迁移数据到 SQLite
"""

import os
import sqlite3
import sys

def migrate_from_duckdb(duckdb_path, sqlite_path):
    """从 DuckDB 迁移数据到 SQLite"""
    try:
        import duckdb
    except ImportError:
        print("❌ 请先安装 duckdb: pip install duckdb")
        sys.exit(1)
    
    # 连接 DuckDB
    duck_db = duckdb.connect(duckdb_path, read_only=True)
    
    # 获取所有表
    tables = duck_db.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]
    
    print(f"📦 发现 {len(table_names)} 个表: {table_names}")
    
    # 连接 SQLite
    if os.path.exists(sqlite_path):
        os.remove(sqlite_path)
    
    sqlite_db = sqlite3.connect(sqlite_path)
    sqlite_cursor = sqlite_db.cursor()
    
    for table_name in table_names:
        print(f"\n🔄 迁移表: {table_name}")
        
        # 获取表结构
        try:
            # 获取列信息
            columns = duck_db.execute(f"DESCRIBE {table_name}").fetchall()
            column_defs = []
            primary_key = None
            
            for col in columns:
                col_name = col[0]
                col_type = col[1]
                
                # 转换类型
                sqlite_type = convert_type(col_type)
                
                # 检查主键
                if 'PRIMARY KEY' in str(col).upper():
                    primary_key = col_name
                    column_defs.append(f"{col_name} {sqlite_type} PRIMARY KEY")
                elif col_name.lower() == 'id':
                    column_defs.append(f"{col_name} {sqlite_type} PRIMARY KEY")
                else:
                    column_defs.append(f"{col_name} {sqlite_type}")
            
            # 创建表
            create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_defs)})"
            sqlite_cursor.execute(create_sql)
            
            # 获取数据
            data = duck_db.execute(f"SELECT * FROM {table_name}").fetchall()
            
            if data:
                # 构建插入语句
                placeholders = ','.join(['?' for _ in range(len(columns))])
                insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
                
                # 批量插入
                sqlite_cursor.executemany(insert_sql, data)
                print(f"✅ 成功迁移 {len(data)} 条记录")
            else:
                print(f"ℹ️ 表 {table_name} 为空")
                
            sqlite_db.commit()
            
        except Exception as e:
            print(f"❌ 迁移表 {table_name} 失败: {e}")
            sqlite_db.rollback()
    
    sqlite_db.close()
    duck_db.close()
    
    print(f"\n🎉 迁移完成！数据已保存到 {sqlite_path}")

def convert_type(duckdb_type):
    """转换 DuckDB 类型到 SQLite 类型"""
    duckdb_type = str(duckdb_type).upper()
    
    if 'INTEGER' in duckdb_type:
        return 'INTEGER'
    elif 'BIGINT' in duckdb_type:
        return 'BIGINT'
    elif 'VARCHAR' in duckdb_type:
        return 'TEXT'
    elif 'TEXT' in duckdb_type:
        return 'TEXT'
    elif 'BOOLEAN' in duckdb_type:
        return 'INTEGER'
    elif 'TIMESTAMP' in duckdb_type:
        return 'TEXT'
    elif 'FLOAT' in duckdb_type or 'DOUBLE' in duckdb_type:
        return 'REAL'
    elif 'DATE' in duckdb_type:
        return 'TEXT'
    else:
        return 'TEXT'

if __name__ == "__main__":
    duckdb_path = '/workspace/cmdb_server_lite/cmdb.duckdb'
    sqlite_path = '/workspace/cmdb_server_lite/cmdb_dev.db'
    
    if not os.path.exists(duckdb_path):
        print(f"❌ DuckDB 文件不存在: {duckdb_path}")
        sys.exit(1)
    
    print(f"🚀 开始从 DuckDB 迁移数据到 SQLite")
    print(f"📥 源文件: {duckdb_path}")
    print(f"📤 目标文件: {sqlite_path}")
    
    migrate_from_duckdb(duckdb_path, sqlite_path)