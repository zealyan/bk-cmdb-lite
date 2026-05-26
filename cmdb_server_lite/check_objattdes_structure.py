import duckdb

# 连接数据库
db = duckdb.connect('cmdb.duckdb')

try:
    print("=== cc_ObjAttDes 表结构 ===")
    columns = db.execute("PRAGMA table_info(cc_ObjAttDes)").fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    print("\n=== 查看一条现有数据 ===")
    sample = db.execute("SELECT * FROM cc_ObjAttDes LIMIT 1").fetchone()
    if sample:
        print(f"  字段数: {len(sample)}")
        # 打印字段名和值
        col_names = [col[1] for col in columns]
        for i, (name, value) in enumerate(zip(col_names, sample)):
            print(f"  {i}: {name} = {value}")

finally:
    db.close()
