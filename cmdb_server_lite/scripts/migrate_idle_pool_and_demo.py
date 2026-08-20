"""
迁移脚本：修复懒加载改造引入的回归
  1) 为每个业务补建「空闲机池」(default=1 的 set，bk_parent_id=biz) + 空闲机(default=1)/故障机(default=2) 模块。
     空闲机池始终位于业务(biz)下首位、且不受自定义主线模型(sys/subsys)顺序影响。
  2) 为之前空白的业务(biz1/2/4/5) 补充演示用 集群(set)+模块(module)，使 biz→set→module 在 UI 正常展示。

用法：cd cmdb_server_lite && python3 scripts/migrate_idle_pool_and_demo.py
"""
import logging
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
import sys
sys.path.insert(0, '.')
from app import create_app
from app.db.executor import query_all, query_one, execute
from app.service.topo_service import create_mainline_instance, clear_topo_cache

app = create_app()


def set_default(table, id_field, inst_id, default_val):
    execute(f'UPDATE "{table}" SET "default" = :d WHERE "{id_field}" = :id AND bk_supplier_account = \'0\'',
            {'d': default_val, 'id': inst_id})


def ensure_idle_pool(biz_id):
    """创建空闲机池（若已存在则跳过）。返回 set_id 或 None。"""
    existing = query_one(
        'SELECT bk_set_id FROM cc_SetBase WHERE bk_biz_id=:b AND bk_supplier_account=\'0\' AND "default"=1',
        {'b': biz_id})
    if existing:
        return existing['bk_set_id']

    res = create_mainline_instance('biz', biz_id, 'set', ['空闲机池'])
    if not res.get('created'):
        print(f"  [warn] biz{biz_id} 创建空闲机池失败: {res.get('error_names')}")
        return None
    set_id = res['created'][0]['bk_set_id']
    set_default('cc_SetBase', 'bk_set_id', set_id, 1)

    mres = create_mainline_instance('set', set_id, 'module', ['空闲机', '故障机'])
    mids = [m['bk_module_id'] for m in mres.get('created', [])]
    if len(mids) >= 2:
        set_default('cc_ModuleBase', 'bk_module_id', mids[0], 1)  # 空闲机
        set_default('cc_ModuleBase', 'bk_module_id', mids[1], 2)  # 故障机
    print(f"  biz{biz_id} 已创建空闲机池 set={set_id}, 模块={mids}")
    return set_id


def ensure_demo_topo(biz_id, n_sets=3, n_modules=2):
    """为空白业务补充演示用 集群+模块（直接挂在 biz 下，bk_parent_id=biz）。"""
    existing = query_one(
        'SELECT COUNT(*) AS c FROM cc_SetBase WHERE bk_biz_id=:b AND bk_supplier_account=\'0\' AND "default"=0',
        {'b': biz_id})
    if existing and existing['c'] > 0:
        print(f"  biz{biz_id} 已有普通集群 {existing['c']} 个，跳过演示数据")
        return
    for i in range(1, n_sets + 1):
        sres = create_mainline_instance('biz', biz_id, 'set', [f'演示集群{i}'])
        if not sres.get('created'):
            print(f"  [warn] biz{biz_id} 创建演示集群{i}失败: {sres.get('error_names')}")
            continue
        sid = sres['created'][0]['bk_set_id']
        names = [f'演示模块{i}-{j}' for j in range(1, n_modules + 1)]
        create_mainline_instance('set', sid, 'module', names)
    print(f"  biz{biz_id} 已创建 {n_sets} 个演示集群(各 {n_modules} 模块)")


with app.app_context():
    bizs = query_all("SELECT bk_biz_id FROM cc_ApplicationBase ORDER BY bk_biz_id")
    print(f"共 {len(bizs)} 个业务，开始迁移...")
    for b in bizs:
        biz_id = b['bk_biz_id']
        print(f"--- biz{biz_id} ---")
        ensure_idle_pool(biz_id)
    # 仅为空白业务补充演示拓扑
    for b in bizs:
        biz_id = b['bk_biz_id']
        ensure_demo_topo(biz_id)
    clear_topo_cache()
    print("缓存已清空，迁移完成。请重启后端使内存缓存(biz-topo)失效并重建。")
