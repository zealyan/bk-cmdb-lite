import sys, logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
sys.path.insert(0, '.')
from app import create_app
from app.db.executor import query_all, query_one
app = create_app()
with app.app_context():
    bizs = query_all("SELECT bk_biz_id, bk_biz_name FROM cc_ApplicationBase ORDER BY bk_biz_id")
    print("=== 业务列表 ===")
    for b in bizs:
        print("  biz", b['bk_biz_id'], b['bk_biz_name'])
    print()
    for b in bizs:
        biz_id = b['bk_biz_id']
        print(f"=== biz{biz_id} 主线实例统计 ===")
        for tbl in ["cc_SetBase","cc_ModuleBase","cc_ObjectBase_0_pub_sys","cc_ObjectBase_0_pub_subsys"]:
            try:
                n = query_one(f"SELECT COUNT(*) AS c FROM \"{tbl}\" WHERE bk_biz_id=:b AND bk_supplier_account='0'", {"b":biz_id})
                print(f"  {tbl}: {n['c']}")
            except Exception as e:
                print(f"  {tbl}: ERR {type(e).__name__}: {str(e)[:100]}")
        try:
            idle = query_all('SELECT bk_set_id, bk_set_name, "default" AS d, bk_parent_id FROM cc_SetBase WHERE bk_biz_id=:b AND bk_supplier_account=\'0\' AND "default"=1', {"b":biz_id})
            print(f"  空闲机池(default=1) set: {[(r['bk_set_id'], r['bk_set_name'], 'parent='+str(r['bk_parent_id'])) for r in idle]}")
        except Exception as e:
            print(f"  空闲机池查询 ERR: {type(e).__name__}: {str(e)[:100]}")
        print()
