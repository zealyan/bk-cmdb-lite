import duckdb

db = duckdb.connect('/workspace/bk-cmdb/cmdb_server_lite/cmdb.duckdb')

result = db.execute("SELECT COUNT(*) as cnt FROM cc_InstAsst_0_pub").fetchone()
print(f"Total associations in database: {result[0]}")

if result[0] > 0:
    print("\nRecent associations:")
    data = db.execute("SELECT * FROM cc_InstAsst_0_pub ORDER BY id DESC LIMIT 5").fetchall()
    columns = [desc[0] for desc in db.description]
    for row in data:
        row_dict = dict(zip(columns, row))
        print(row_dict)

db.close()
