import logging
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
import sys
sys.path.insert(0, '.')
from app import create_app
from app.db.executor import query_all
app = create_app()
with app.app_context():
    tabs = query_all("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%Obj%'")
    print("Obj 相关表:", [t['name'] for t in tabs])
    for t in ['cc_ObjDes', 'cc_ClassBase', 'cc_ObjAsst', 'cc_ModelBase']:
        try:
            cols = query_all(f"PRAGMA table_info('{t}')")
            print(f"{t} 列:", [c['name'] for c in cols][:30])
        except Exception as e:
            print(t, "ERR", str(e)[:80])
    print("--- 含 bk_obj_name+bk_obj_id 的表 ---")
    allt = query_all("SELECT name FROM sqlite_master WHERE type='table'")
    for r in allt:
        t = r['name']
        try:
            cols = [c['name'] for c in query_all(f"PRAGMA table_info('{t}')")]
            if 'bk_obj_name' in cols and 'bk_obj_id' in cols:
                print(t, cols[:15])
        except Exception:
            pass
