import duckdb

db = duckdb.connect('/workspace/bk-cmdb/cmdb_server_lite/cmdb.duckdb')

# 查询最近创建的关联
print("=== 检查最近的关联数据 ===")

# 查询所有 bk_slb 相关的关联
assocs = db.execute("""
    SELECT id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id, 
           bk_obj_asst_id, bk_relation_type_id
    FROM cc_InstAsst_0_pub 
    WHERE bk_obj_id = 'bk_slb'
    ORDER BY id DESC
    LIMIT 10
""").fetchall()

if assocs:
    columns = ['id', 'bk_obj_id', 'bk_inst_id', 'bk_asst_obj_id', 'bk_asst_inst_id', 'bk_obj_asst_id', 'bk_relation_type_id']
    print(f"找到 {len(assocs)} 条关联记录：")
    for row in assocs:
        print(f"\n  ID: {row[0]}")
        print(f"    {columns[1]}: {row[1]}")
        print(f"    {columns[2]}: {row[2]}")
        print(f"    {columns[3]}: {row[3]}")
        print(f"    {columns[4]}: {row[4]}")
        print(f"    {columns[5]}: {row[5]}")
        print(f"    {columns[6]}: {row[6]}")

# 测试查询逻辑
print("\n=== 测试查询逻辑 ===")

# 模拟前端查询 - 查询 bk_slb:1 的关联
test_query = db.execute("""
    SELECT * FROM cc_InstAsst_0_pub 
    WHERE bk_obj_id = 'bk_slb'
      AND bk_asst_obj_id = 'bk_slb_server'
""").fetchall()

print(f"\n查询 bk_slb -> bk_slb_server: {len(test_query)} 条")

db.close()
