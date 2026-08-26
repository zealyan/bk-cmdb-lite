#!/usr/bin/env python3
"""
自定义业务拓扑模型（多模型多层级）e2e 验证

验证范围（对齐上游 bk-cmdb 主线模型设计）：
1. 迁移：自定义实例表补 bk_biz_id/bk_parent_id/default 列 + cc_ObjAsst 种子化 bk_mainline 关联
2. CLI：mainline add/show/remove（含自动建模型、旧子重挂、spawn 批量回填实例）
3. 服务层：create_mainline_instance 通写 bk_parent_id/bk_biz_id；get_mainline_instance_topo 动态拼装 N 层实例树
4. 删除：摘除自定义层级并重挂子级、清理实例

隔离说明：DevelopmentConfig.DATABASE_NAME 为硬编码字面量，env 无效。
故在导入后覆盖该值并重置引擎单例，使全程落在 cmdb_dev_e2e.db 副本上，不污染 cmdb_dev.db。
"""
import os
import shutil
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_DB = ROOT / 'cmdb_dev.db'
E2E_DB = ROOT / 'cmdb_dev_e2e.db'

sys.path.insert(0, str(ROOT))

# —— 隔离：覆盖硬编码 DB 名 + 重置引擎单例（必须在首次引擎访问前）——
import app.config.settings as _settings
_DTYPE = os.environ.get('CMDB_DATABASE_TYPE', 'sqlite')
if _DTYPE == 'sqlite':
    _settings.DevelopmentConfig.DATABASE_NAME = E2E_DB.name
    from app.db.engine import db_engine
    db_engine._engine = None
    db_engine._session_factory = None
    if E2E_DB.exists():
        E2E_DB.unlink()
    shutil.copy(SRC_DB, E2E_DB)
else:
    # 非 SQLite：在服务端预建测试库，避免污染开发库（三库方言验证用）
    import sqlalchemy
    E2E_DB_NAME = f'cmdb_e2e_{_DTYPE}'
    _settings.DevelopmentConfig.DATABASE_NAME = E2E_DB_NAME
    if _DTYPE == 'postgresql':
        _admin = sqlalchemy.create_engine(
            'postgresql://postgres:postgres@127.0.0.1:5432/postgres')
        with _admin.connect() as _c:
            _c.execution_options(isolation_level='AUTOCOMMIT')
            _c.execute(sqlalchemy.text(f'DROP DATABASE IF EXISTS {E2E_DB_NAME}'))
            _c.execute(sqlalchemy.text(f'CREATE DATABASE {E2E_DB_NAME}'))
    elif _DTYPE == 'mysql':
        _admin = sqlalchemy.create_engine(
            'mysql+pymysql://root:root@127.0.0.1:3306/')
        with _admin.connect() as _c:
            _c.execute(sqlalchemy.text(f'DROP DATABASE IF EXISTS {E2E_DB_NAME}'))
            _c.execute(sqlalchemy.text(f'CREATE DATABASE {E2E_DB_NAME}'))
    from app.db.engine import db_engine
    db_engine._engine = None
    db_engine._session_factory = None
    # 先跑完整迁移，建立 schema + 种子
    from app.migrate.migrate import DatabaseMigrator
    DatabaseMigrator().migrate()

from app.migrate.migrate import DatabaseMigrator
from app.cli import db as dbmod
from app.db.dialect import get_column_names
from app.cli.cmdb import (
    add_mainline_core, remove_mainline_core, show_mainline_core,
    cmd_mainline_add, cmd_mainline_show, cmd_mainline_remove,
)
from app.service.topo_service import (
    get_mainline_model_top, create_mainline_instance,
    get_mainline_instance_topo, create_set, create_module,
)
from app.service.instance_service import InstanceService

PASS = 0
FAIL = 0


def check(name, cond, detail=''):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


def run_migrate_cols_and_seed():
    m = DatabaseMigrator()
    m.ensure_mainline_columns()
    m.migrate_mainline_associations()


def chain():
    return get_mainline_model_top('0').leftest_object_id_list()


def inst_table_cols(model_id):
    """取自定义实例表列名（跨库通用，取代 PRAGMA table_info 内省）。"""
    tbl = InstanceService._get_table_name(model_id)
    return set(get_column_names(tbl))


def inst_rows(model_id, biz=None):
    tbl = InstanceService._get_table_name(model_id)
    sql = f'SELECT * FROM "{tbl}" WHERE bk_supplier_account=:sup'
    params = {'sup': '0'}
    if biz is not None:
        sql += ' AND bk_biz_id=:biz'
        params['biz'] = biz
    with dbmod.cli_conn() as c:
        return c.query_all(sql, params)


def inst_row_by_id(model_id, inst_id):
    """按主键精确取某实例一行（避免取到同名/历史实例）。"""
    tbl = InstanceService._get_table_name(model_id)
    id_field = InstanceService._get_id_field(model_id)
    sql = f'SELECT * FROM "{tbl}" WHERE "{id_field}"=:i AND bk_supplier_account=:sup'
    with dbmod.cli_conn() as c:
        return c.query_one(sql, {'i': inst_id, 'sup': '0'})


def ns(**kw):
    return types.SimpleNamespace(**kw)


try:
    # =======================================================================
    print("=== 场景1：spawn 批量回填实例（为父下每个实例生成一级子实例）===")
    run_migrate_cols_and_seed()
    check("种子化后主线链 biz->set->module", chain() == ['biz', 'set', 'module'],
          f"实际 {chain()}")
    check("自定义实例表含 bk_parent_id", 'bk_parent_id' in inst_table_cols('bk_slb'))
    check("自定义实例表含 bk_biz_id", 'bk_biz_id' in inst_table_cols('bk_slb'))

    biz_count = len(inst_rows('biz'))
    with dbmod.cli_conn() as c:
        with c.conn.begin():
            r = add_mainline_core(c, 'floor', 'biz',
                                  {'obj_name': '楼层', 'spawn': True}, False)
    check(f"spawn 生成 {biz_count} 个 floor 实例", r.get('spawned') == biz_count,
          f"实际 spawned={r.get('spawned')}, biz={biz_count}")
    floors = inst_rows('floor')
    check("floor 实例数 == 业务数", len(floors) == biz_count, f"实际 {len(floors)}")
    check("floor 实例 bk_parent_id 继承父(biz)",
          all(f.get('bk_parent_id') == f.get('bk_biz_id') for f in floors),
          "bk_parent_id 应等于其业务ID")
    check("spawn 后主线链含 floor", 'floor' in chain(), f"实际 {chain()}")

    with dbmod.cli_conn() as c:
        with c.conn.begin():
            remove_mainline_core(c, 'floor', delete_instances=True, dry_run=False)
    check("摘除 floor 后主线链恢复", chain() == ['biz', 'set', 'module'], f"实际 {chain()}")
    check("摘除并删实例后 floor 表清空", len(inst_rows('floor')) == 0)

    # =======================================================================
    print("=== 场景2：自定义多模型多层级（biz->rack->set->zone->module）===")
    with dbmod.cli_conn() as c:
        with c.conn.begin():
            add_mainline_core(c, 'rack', 'biz', {'obj_name': '机柜'}, False)
        with c.conn.begin():
            add_mainline_core(c, 'zone', 'set', {'obj_name': '区域'}, False)
    check("主线链 biz->rack->set->zone->module",
          chain() == ['biz', 'rack', 'set', 'zone', 'module'], f"实际 {chain()}")

    # 自顶向下为业务 2 创建实例（bk_parent_id 逐级指向上级实例）
    r_biz2_rack = create_mainline_instance('biz', 2, 'rack', ['rack-2'])
    rack2 = r_biz2_rack['created'][0]['bk_inst_id']
    check("rack 实例建于业务2下", len(r_biz2_rack['created']) == 1 and
          r_biz2_rack['created'][0]['bk_biz_id'] == 2)
    check("rack 实例 bk_parent_id == 2", r_biz2_rack['created'][0]['bk_parent_id'] == 2)

    r_set = create_mainline_instance('rack', rack2, 'set', ['set-2'])
    set2 = r_set['created'][0]['bk_inst_id']
    check("set 实例 bk_parent_id == rack2", r_set['created'][0]['bk_parent_id'] == rack2,
          f"bk_parent_id={r_set['created'][0]['bk_parent_id']}, rack2={rack2}")
    check("set 实例 bk_biz_id == 2", r_set['created'][0]['bk_biz_id'] == 2)

    r_zone = create_mainline_instance('set', set2, 'zone', ['zone-2'])
    zone2 = r_zone['created'][0]['bk_inst_id']
    check("zone 实例 bk_parent_id == set2", r_zone['created'][0]['bk_parent_id'] == set2,
          f"bk_parent_id={r_zone['created'][0]['bk_parent_id']}, set2={set2}")
    check("zone 实例 bk_biz_id == 2", r_zone['created'][0]['bk_biz_id'] == 2)

    r_mod = create_mainline_instance('zone', zone2, 'module', ['mod-2'])
    mod2 = r_mod['created'][0]['bk_inst_id']
    check("module 实例 bk_parent_id == zone2", r_mod['created'][0]['bk_parent_id'] == zone2,
          f"bk_parent_id={r_mod['created'][0]['bk_parent_id']}, zone2={zone2}")
    check("module 实例 bk_biz_id == 2", r_mod['created'][0]['bk_biz_id'] == 2)
    mod_row = inst_row_by_id('module', mod2)
    check("module 实例 bk_set_id 兼容列回填", mod_row.get('bk_set_id') == set2,
          f"bk_set_id={mod_row.get('bk_set_id')}")

    # 插一台主机到 mod-2，验证统计沿主线自底向上聚合（count = 主机数）
    host = InstanceService.create_instance('host', {
        'bk_host_name': 'h-2', 'bk_host_innerip': '10.0.0.2',
        'bk_biz_id': 2, 'bk_set_id': set2, 'bk_module_id': mod2,
        'bk_supplier_account': '0',
    })
    host_id = host.get('bk_host_id')
    with dbmod.cli_conn() as c:
        with c.conn.begin():
            c.exec(
                'INSERT INTO cc_ModuleHostConfig '
                '(bk_biz_id, bk_host_id, bk_module_id, bk_set_id, bk_supplier_account) '
                'VALUES (:b, :h, :m, :s, :sup)',
                {'b': 2, 'h': host_id, 'm': mod2, 's': set2, 'sup': '0'})

    # 动态实例树（N 层）
    tree = get_mainline_instance_topo(2, with_statistics=True)
    check("根节点为业务2", tree.object_id == 'biz' and tree.instance_id == 2)
    rack_nodes = [n for n in tree.children if n.object_id == 'rack']
    check("业务2下含 rack-2", any(n.instance_id == rack2 for n in rack_nodes))
    rack_node = next(n for n in rack_nodes if n.instance_id == rack2)
    set_nodes = [n for n in rack_node.children if n.object_id == 'set']
    check("rack-2 下含 set-2", any(n.instance_id == set2 for n in set_nodes))
    set_node = next(n for n in set_nodes if n.instance_id == set2)
    zone_nodes = [n for n in set_node.children if n.object_id == 'zone']
    check("set-2 下含 zone-2", any(n.instance_id == zone2 for n in zone_nodes))
    zone_node = next(n for n in zone_nodes if n.instance_id == zone2)
    mod_nodes = [n for n in zone_node.children if n.object_id == 'module']
    check("zone-2 下含 mod-2", any(n.instance_id == mod2 for n in mod_nodes))
    mod_node = next(n for n in mod_nodes if n.instance_id == mod2)
    check("module 主机数 == 1", mod_node.count == 1, f"mod.count={mod_node.count}")
    check("统计沿主线聚合上溯（rack.count == 1）", rack_node.count == 1,
          f"rack.count={rack_node.count}")

    # 摘除自定义层级（先 zone 后 rack），验证重挂与实例清理
    with dbmod.cli_conn() as c:
        with c.conn.begin():
            remove_mainline_core(c, 'zone', delete_instances=True, dry_run=False)
    check("摘除 zone 后链 biz->rack->set->module", chain() == ['biz', 'rack', 'set', 'module'],
          f"实际 {chain()}")
    check("zone 实例已清理", len(inst_rows('zone')) == 0)
    check("module 重挂回 set（bk_parent_id==set2）",
          inst_row_by_id('module', mod2).get('bk_parent_id') == set2,
          f"bk_parent_id={inst_row_by_id('module', mod2).get('bk_parent_id')}, set2={set2}")

    with dbmod.cli_conn() as c:
        with c.conn.begin():
            remove_mainline_core(c, 'rack', delete_instances=True, dry_run=False)
    check("摘除 rack 后链恢复 biz->set->module", chain() == ['biz', 'set', 'module'],
          f"实际 {chain()}")
    check("rack 实例已清理", len(inst_rows('rack')) == 0)
    check("set 实例 bk_parent_id 回指业务2",
          inst_row_by_id('set', set2).get('bk_parent_id') == 2,
          f"bk_parent_id={inst_row_by_id('set', set2).get('bk_parent_id')}")

    # =======================================================================
    print("=== 场景3：CLI 子命令（cmd_* 进程内调用）===")
    r = cmd_mainline_add(ns(obj_id='room', parent='set', obj_name='机房',
                            classification='bk_biz_topo', icon='icon-cc-default',
                            obj_sort_number=0, spawn=False, dry_run=False, json=False))
    check("CLI mainline add 成功", r == 0)
    check("CLI add 后链含 room", 'room' in chain(), f"实际 {chain()}")
    r = cmd_mainline_show(ns(json=False))
    check("CLI mainline show 成功", r == 0)
    r = cmd_mainline_remove(ns(obj_id='room', delete_instances=True,
                               dry_run=False, json=False))
    check("CLI mainline remove 成功", r == 0)
    check("CLI remove 后链恢复", chain() == ['biz', 'set', 'module'], f"实际 {chain()}")

    # 标准链回归：create_set / create_module 仍可用
    cs = create_set(2, ['regression-set'])
    check("create_set 回归可用", len(cs['created']) == 1)
    cm = create_module(cs['created'][0]['bk_set_id'], ['regression-mod'], bk_biz_id=2)
    check("create_module 回归可用", len(cm['created']) == 1)

finally:
    if E2E_DB.exists():
        E2E_DB.unlink()

print(f"\n=== 结果：PASS={PASS} FAIL={FAIL} ===")
sys.exit(1 if FAIL else 0)
