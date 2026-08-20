"""
迁移脚本：修复 CLI 创建 biz3 自定义主线后暴露的两类 mainline 问题
  1) 修复 cc_ObjAsst 中 set 关联记录字段不一致：
     重挂后 target_obj_id='subsys'，但 bk_obj_asst_id 仍为 set_mainline_biz、
     bk_obj_asst_name/target_obj_name 仍为 "属于业务/业务" → 统一为 subsys 语义。
  2) 统一所有 biz 结构：全局主线已是 biz→sys→subsys→set→module，
     为空白业务(1/2/4/5)补 sys（父=biz）+ subsys（父=sys）实例层，
     并把挂在 biz 下的普通 set（演示集群，default=0）重挂到 subsys 下，
     使所有 biz 均遵循同一主线结构；空闲机池(default=1)保持直挂 biz（内置规则）。

用法：cd cmdb_server_lite && python3 scripts/unify_mainline_structure.py
"""
import logging
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
import sys
sys.path.insert(0, '.')
from app import create_app
from app.db.executor import query_all, query_one, execute
from app.service.topo_service import (
    create_mainline_instance, clear_topo_cache,
    get_mainline_model_top,
)

app = create_app()


def fix_stale_set_association():
    """修复 set 关联记录字段（target 已是 subsys 但 ID/名称仍指向 biz）。"""
    row = query_one(
        "SELECT bk_obj_id, target_obj_id, bk_obj_asst_id FROM cc_ObjAsst "
        "WHERE bk_asst_id='bk_mainline' AND bk_obj_id='set' AND target_obj_id='subsys'")
    if not row:
        print("  [skip] 未找到 set->subsys 关联记录（可能已修复）")
        return
    if row['bk_obj_asst_id'] == 'set_mainline_subsys':
        print("  [skip] set 关联记录已一致（set_mainline_subsys）")
        return
    execute(
        "UPDATE cc_ObjAsst SET target_obj_name='应用子系统', "
        "bk_obj_asst_id='set_mainline_subsys', bk_obj_asst_name='属于应用子系统' "
        "WHERE bk_asst_id='bk_mainline' AND bk_obj_id='set' AND target_obj_id='subsys'")
    print(f"  已修复 set 关联记录: {row['bk_obj_asst_id']} -> set_mainline_subsys / 属于应用子系统")


def unify_empty_biz(biz_id):
    """为空白业务补 sys/subsys 层，并把普通 set 重挂到 subsys 下。"""
    # 已有 sys 实例则跳过
    exist_sys = query_one(
        "SELECT bk_inst_id FROM cc_ObjectBase_0_pub_sys "
        "WHERE bk_biz_id=:b AND bk_supplier_account='0' LIMIT 1", {'b': biz_id})
    if exist_sys:
        print(f"  biz{biz_id} 已有 sys 层，跳过")
        return

    # 1) 建 sys（父=biz）
    sres = create_mainline_instance('biz', biz_id, 'sys', ['应用系统'])
    if not sres.get('created'):
        print(f"  [warn] biz{biz_id} 创建 sys 失败: {sres.get('error_names')}")
        return
    sys_id = sres['created'][0]['bk_inst_id']

    # 2) 建 subsys（父=sys）
    ssres = create_mainline_instance('sys', sys_id, 'subsys', ['应用子系统'])
    if not ssres.get('created'):
        print(f"  [warn] biz{biz_id} 创建 subsys 失败: {ssres.get('error_names')}")
        return
    subsys_id = ssres['created'][0]['bk_inst_id']

    # 3) 把挂在 biz 下的普通 set（default=0）重挂到 subsys 下；空闲机池(default=1)保留直挂 biz
    before = query_one(
        "SELECT COUNT(*) AS c FROM cc_SetBase "
        "WHERE bk_biz_id=:b AND bk_supplier_account='0' AND \"default\"=0 AND bk_parent_id=:b",
        {'b': biz_id})
    execute(
        "UPDATE cc_SetBase SET bk_parent_id=:sub "
        "WHERE bk_biz_id=:b AND bk_supplier_account='0' AND \"default\"=0 AND bk_parent_id=:b",
        {'sub': subsys_id, 'b': biz_id})
    print(f"  biz{biz_id} 已建 sys={sys_id} subsys={subsys_id}，重挂普通 set {before['c'] if before else 0} 个 → subsys 下")


with app.app_context():
    print("=== 1) 修复 set 关联记录字段 ===")
    fix_stale_set_association()

    print()
    print("=== 2) 统一所有 biz 主线结构 ===")
    chain = get_mainline_model_top('0').leftest_object_id_list()
    print(f"  当前全局主线: {' -> '.join(chain)}")
    bizs = query_all("SELECT bk_biz_id FROM cc_ApplicationBase ORDER BY bk_biz_id")
    for b in bizs:
        unify_empty_biz(b['bk_biz_id'])

    clear_topo_cache()
    print()
    print("缓存已清空，迁移完成。请重启后端使内存缓存(biz-topo)失效并重建。")
