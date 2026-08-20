import duckdb

db = duckdb.connect('/workspace/bk-cmdb/cmdb_server_lite/cmdb.duckdb')

# 查询所有 slb 相关的关联，不设限制
print("=== 查询所有 bk_slb 相关的关联:")
data = db.execute("SELECT * FROM cc_InstAsst_0_pub WHERE bk_obj_id LIKE '%slb%' OR bk_asst_obj_id LIKE '%slb%' ORDER BY id DESC LIMIT 20").fetchall()
columns = [desc[0] for desc in db.description]

for row in data:
    row_dict = dict(zip(columns, row))
    print(f"ID: {row_dict['id']}")
    print(f"  Source: {row_dict['bk_obj_id']} [{row_dict['bk_inst_id']}]")
    print(f"  Target: {row_dict['bk_asst_obj_id']} [{row_dict['bk_asst_inst_id']}]")
    print(f"  bk_obj_asst_id: {row_dict['bk_obj_asst_id']}")
    print(f"  bk_relation_type_id: {row_dict['bk_relation_type_id']}")
    print("-" * 60)

db.close()
