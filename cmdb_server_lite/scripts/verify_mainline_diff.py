"""
验证 CLI mainline 对齐原项目的三个差异点（事务内构造模拟数据，结束后 ROLLBACK 不落库）：
  A) _reparent_mainline_instances：空闲机池(default=1 set)不参与重挂
  B) _reparent_mainline_instances：自动生成实例名剔除主线特殊字符 [#/,><|]
  C) remove_mainline_core：子实例上提后的重名预检（对齐上游 checkInstNameRepeat）
"""
import logging
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
import sys
import traceback
sys.path.insert(0, '.')
from app.cli import db as dbmod
from app.cli.db import init_cli_db, CliConn
from app.cli.cmdb import _reparent_mainline_instances, remove_mainline_core, INSTANCE_TABLE_DDL
from app.cli.errors import CliError
from app.utils.tools import generate_id

engine = init_cli_db()
conn = engine.connect()
tx = conn.begin()
c = CliConn(conn)
results = []


def record(name, ok, detail=''):
    results.append((name, ok, detail))
    print(f"  [{'✓' if ok else '✗'}] {name} {detail}")


# ---------- Part A+B: _reparent_mainline_instances ----------
print("=== A+B) _reparent_mainline_instances：空闲机池过滤 + 名称特殊字符过滤 ===")
try:
    c.exec(INSTANCE_TABLE_DDL.format(tbl='cc_ObjectBase_0_pub_p'))
    c.exec(INSTANCE_TABLE_DDL.format(tbl='cc_ObjectBase_0_pub_n'))
    p1 = 90001
    c.exec('INSERT INTO cc_ObjectBase_0_pub_p (bk_inst_id, bk_inst_name, bk_supplier_account, '
           "bk_obj_id, bk_biz_id, bk_parent_id, \"default\") VALUES (:i,:n,'0','p',999,0,0)",
           {'i': p1, 'n': 'P1'})
    idle_set, norm_set = 91001, 91002
    c.exec('INSERT INTO cc_SetBase (bk_set_id, bk_set_name, bk_supplier_account, bk_biz_id, '
           'bk_parent_id, "default") VALUES (:i,:n,\'0\',999,:p,1)',
           {'i': idle_set, 'n': '空闲机池', 'p': p1})
    c.exec('INSERT INTO cc_SetBase (bk_set_id, bk_set_name, bk_supplier_account, bk_biz_id, '
           'bk_parent_id, "default") VALUES (:i,:n,\'0\',999,:p,0)',
           {'i': norm_set, 'n': '集群A', 'p': p1})

    n = _reparent_mainline_instances(c, 'p', 'n', 'set', '新区#/层>')
    assert n == 1, f"期望重挂 1 个普通 set，实际 {n}"
    new_rows = c.query_all('SELECT bk_inst_id, bk_inst_name, bk_parent_id FROM cc_ObjectBase_0_pub_n')
    assert len(new_rows) == 1, f"期望 1 个新层实例，实际 {len(new_rows)}"
    nn = new_rows[0]
    assert nn['bk_inst_name'] == '新区层_P1', f"名称未剔除特殊字符: {nn['bk_inst_name']!r}"
    assert nn['bk_parent_id'] == p1
    idle = c.query_one('SELECT bk_parent_id FROM cc_SetBase WHERE bk_set_id=:i', {'i': idle_set})
    norm = c.query_one('SELECT bk_parent_id FROM cc_SetBase WHERE bk_set_id=:i', {'i': norm_set})
    assert idle['bk_parent_id'] == p1, f"空闲机池被错误重挂: {idle['bk_parent_id']}"
    assert norm['bk_parent_id'] == nn['bk_inst_id'], f"普通集群未重挂到新层: {norm['bk_parent_id']}"
    record('重挂普通 set 1 个；新层实例名=%s；空闲机池保持 bk_parent_id=%s' % (nn['bk_inst_name'], idle['bk_parent_id']), True)
except Exception:
    traceback.print_exc()
    record('A+B 执行失败', False)

# ---------- Part C: remove_mainline_core 重名预检 ----------
print()
print("=== C) remove_mainline_core：子实例上提重名预检 ===")
try:
    c.exec(INSTANCE_TABLE_DDL.format(tbl='cc_ObjectBase_0_pub_test_parent'))
    c.exec(INSTANCE_TABLE_DDL.format(tbl='cc_ObjectBase_0_pub_test_lvl'))
    c.exec(INSTANCE_TABLE_DDL.format(tbl='cc_ObjectBase_0_pub_test_child'))
    c.exec('INSERT INTO cc_ObjAsst (id, bk_obj_id, target_obj_id, target_obj_name, bk_asst_id, '
           "bk_obj_asst_id, bk_obj_asst_name, mapping, on_delete, creator, modifier, bk_supplier_account) "
           "VALUES (:id,'test_lvl','test_parent','父','bk_mainline','test_lvl_mainline_test_parent',"
           "'属于父','1:n','none','admin','admin','0')",
           {'id': generate_id()})
    c.exec('INSERT INTO cc_ObjAsst (id, bk_obj_id, target_obj_id, target_obj_name, bk_asst_id, '
           "bk_obj_asst_id, bk_obj_asst_name, mapping, on_delete, creator, modifier, bk_supplier_account) "
           "VALUES (:id,'test_child','test_lvl','层','bk_mainline','test_child_mainline_test_lvl',"
           "'属于层','1:n','none','admin','admin','0')",
           {'id': generate_id()})
    tp1, tl1 = 92001, 92002
    c.exec('INSERT INTO cc_ObjectBase_0_pub_test_parent (bk_inst_id, bk_inst_name, bk_supplier_account, '
           "bk_obj_id, bk_biz_id, bk_parent_id, \"default\") VALUES (:i,'TP','0','test_parent',1,0,0)",
           {'i': tp1})
    c.exec('INSERT INTO cc_ObjectBase_0_pub_test_lvl (bk_inst_id, bk_inst_name, bk_supplier_account, '
           "bk_obj_id, bk_biz_id, bk_parent_id, \"default\") VALUES (:i,'TL','0','test_lvl',1,:p,0)",
           {'i': tl1, 'p': tp1})
    c.exec('INSERT INTO cc_ObjectBase_0_pub_test_child (bk_inst_id, bk_inst_name, bk_supplier_account, '
           "bk_obj_id, bk_biz_id, bk_parent_id, \"default\") VALUES (:i,'X','0','test_child',1,:p,0)",
           {'i': 92003, 'p': tl1})
    c.exec('INSERT INTO cc_ObjectBase_0_pub_test_child (bk_inst_id, bk_inst_name, bk_supplier_account, '
           "bk_obj_id, bk_biz_id, bk_parent_id, \"default\") VALUES (:i,'X','0','test_child',1,:p,0)",
           {'i': 92004, 'p': tl1})

    # 重名场景：两个子实例都叫 X，上提到 tp1 后冲突 → 应抛 CliError
    try:
        remove_mainline_core(c, 'test_lvl', delete_instances=False, dry_run=False)
        record('重名场景未被拦截(异常)', False)
    except CliError as e:
        record('重名场景被拦截: %s' % e, True)

    # 无重名场景：删除一个子实例后应放行
    c.exec('DELETE FROM cc_ObjectBase_0_pub_test_child WHERE bk_inst_id=:i', {'i': 92004})
    ret = remove_mainline_core(c, 'test_lvl', delete_instances=False, dry_run=False)
    assert ret['action'] == 'delete'
    asst_left = c.query_one(
        "SELECT 1 AS x FROM cc_ObjAsst WHERE bk_asst_id='bk_mainline' AND bk_obj_id='test_lvl'")
    assert asst_left is None, "test_lvl 关联记录未删除"
    record('无重名场景放行 + 关联记录已摘除', True)
except Exception:
    traceback.print_exc()
    record('C 执行失败', False)

# ---------- 回滚与结论 ----------
tx.rollback()
conn.close()
print()
print("事务已回滚，模拟数据未落库。")
all_ok = all(r[1] for r in results)
print("结论:", "全部通过 ✓" if all_ok else "存在失败项 ✗")
sys.exit(0 if all_ok else 1)
