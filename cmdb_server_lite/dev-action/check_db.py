
#!/usr/bin/env python3
import duckdb

db = duckdb.connect('cmdb.duckdb')

print("=== cc_ObjAsst 表数据 ===")
print("\n字段列表:")
columns = db.execute("PRAGMA table_info(cc_ObjAsst)").fetchall()
for col in columns:
    print(f"  {col[1]} ({col[2]})")

print("\n数据内容:")
rows = db.execute("SELECT * FROM cc_ObjAsst").fetchall()
for row in rows:
    print(f"  {row}")

print("\n=== cc_AsstDes 表数据 ===")
rows = db.execute("SELECT * FROM cc_AsstDes").fetchall()
for row in rows:
    print(f"  {row}")

db.close()
