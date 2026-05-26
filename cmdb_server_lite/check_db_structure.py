import duckdb
import sys

# 连接数据库
db = duckdb.connect('cmdb.duckdb')

try:
    print("=== 查看所有表 ===")
    tables = db.execute("SHOW TABLES").fetchall()
    for table in tables:
        print(f"  - {table[0]}")
    
    print("\n=== 查看 cc_ObjDes 表结构 ===")
    try:
        columns = db.execute("PRAGMA table_info(cc_ObjDes)").fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
    except Exception as e:
        print(f"  表不存在: {e}")
    
    print("\n=== 查看 cc_ObjDes 数据 ===")
    try:
        data = db.execute("SELECT * FROM cc_ObjDes").fetchall()
        for row in data:
            print(f"  {row}")
    except Exception as e:
        print(f"  查询失败: {e}")
    
    print("\n=== 查看 cc_ObjClassification 表是否存在 ===")
    try:
        columns = db.execute("PRAGMA table_info(cc_ObjClassification)").fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
    except Exception as e:
        print(f"  表不存在: {e}")

finally:
    db.close()
