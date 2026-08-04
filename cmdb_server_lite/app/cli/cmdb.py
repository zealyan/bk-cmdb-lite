# -*- coding: utf-8 -*-
"""CMDB-Lite 命令行工具（app/cli/cmdb.py）。

按 docs/CLI工具设计文档.md 落地。复用：
- app.db.executor 的连接池 / 事务（app.cli.db）
- app.definitions.get_sql_type（类型→SQL 单一真相源）
- app.migrate.migrate.SYSTEM_PROPERTIES / convert_enum_option（系统属性模板 / 枚举归一）
- app.utils.tools.generate_id（全局唯一 ID）
- app.cli.safety.validate_identifier（C1 标识符安全唯一入口）

退出码（§9）：0 成功 / 1 通用错误·对账不一致 / 2 参数错误·预检失败 / 3 依赖缺失 /
4 已存在且 error / 5 数据库不可达·locked。
"""

import argparse
import json
import os
import sys
import time
from typing import Optional

from sqlalchemy.exc import OperationalError

from app.definitions import get_sql_type, VALID_PROPERTY_TYPES
from app.migrate.migrate import SYSTEM_PROPERTIES, convert_enum_option
from app.utils.tools import generate_id, parse_json
from app.cli.safety import (
    validate_identifier, quote_ident, quote_ident_raw, InvalidIdentifierError)
from app.cli import db as dbmod
from app.cli.io_utils import (
    read_csv_rows, write_seed_csv, sha256_of, coerce_value, parse_bool,
    RejectStore, write_manifest, now_iso, profile_source,
)

# ---------------------------------------------------------------------------
# 退出码（§9）
# ---------------------------------------------------------------------------
EXIT_OK = 0
EXIT_GENERAL = 1
EXIT_PARAM = 2
EXIT_DEP = 3
EXIT_EXISTS = 4
EXIT_DB = 5


class CliError(Exception):
    """带退出码的结构化错误。"""

    def __init__(self, code: int, msg: str, step: Optional[str] = None):
        self.code, self.msg, self.step = code, msg, step
        super().__init__(msg)


# ---------------------------------------------------------------------------
# SQL 模板（与 migrate.py / 指南八 完全一致）
# ---------------------------------------------------------------------------
INSTANCE_TABLE_DDL = """CREATE TABLE IF NOT EXISTS {tbl} (
    _id TEXT,
    id INTEGER PRIMARY KEY,
    bk_inst_id INTEGER NOT NULL,
    bk_inst_name VARCHAR NOT NULL,
    bk_supplier_account VARCHAR DEFAULT '0',
    bk_obj_id VARCHAR NOT NULL,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bk_operate_time TIMESTAMP
)"""

ASSOC_TABLE_DDL = """CREATE TABLE IF NOT EXISTS {tbl} (
    _id TEXT,
    id INTEGER PRIMARY KEY,
    bk_obj_id VARCHAR NOT NULL,
    bk_inst_id INTEGER NOT NULL,
    bk_asst_obj_id VARCHAR NOT NULL,
    bk_asst_inst_id INTEGER NOT NULL,
    bk_obj_asst_id VARCHAR NOT NULL,
    bk_relation_type_id VARCHAR NOT NULL,
    bk_supplier_account VARCHAR DEFAULT '0'
)"""

SQLITE_SYSTEM_COLS = {'_id', 'id', 'bk_inst_id', 'bk_inst_name',
                      'bk_obj_id', 'bk_supplier_account', 'create_time',
                      'last_time', 'bk_operate_time'}

# cc_ObjAttDes 系统属性 INSERT 列（设计文档 §5.2 步骤 5；isonly 现纳入以匹配上游导入规则）
SYS_ATTR_COLS = [
    "_id", "id", "bk_obj_id", "bk_property_id", "bk_property_name", "bk_property_type",
    "bk_property_group", "isrequired", "bk_ispassword", "bk_ishidden", "isreadonly",
    "isonly", "bk_isapi", "bk_issystem", "ispre", "bk_property_index", "unit", "placeholder",
    "editable", "option", "bk_supplier_account",
]

# cc_ObjAttDes 业务属性 INSERT 列（设计文档 §5.3；isonly 现纳入以匹配上游导入规则）
ATTR_COLS = [
    "_id", "id", "bk_obj_id", "bk_property_id", "bk_property_name", "bk_property_type",
    "bk_property_group", "isrequired", "bk_ispassword", "bk_ishidden", "isreadonly",
    "isonly", "bk_isapi", "bk_issystem", "ispre", "ismultiple", "bk_property_index", "option",
    "placeholder", "unit", "editable", "bk_supplier_account",
]

# upsert 更新时排除的标识列（§5.8.2）
UPDATE_EXCLUDE = {'id', 'bk_inst_id', 'bk_obj_id', '_id', 'bk_supplier_account', 'bk_inst_name'}

# 上游已知分组 ID -> 标准显示名（与 app/migrate/migrate.py 的 EXTRA_GROUP_DEFS 保持一致）。
# 分组 ID 一律小写：'default' 来自上游 NewGroupID(true)，'auto' 来自 mCommon.HostAutoFields。
# --group-auto-create 建分组时命中则用标准名，未命中才退回用 ID 当显示名。
KNOWN_GROUP_NAMES = {
    'default': '基础信息',
    'auto': '自动发现信息（需要安装agent）',
    'role': '角色',
    'proc_port': '监听信息',
}


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------
def emit_error(code: int, msg: str, step: Optional[str], json_out: bool):
    if json_out:
        print(json.dumps({"error": msg, "step": step, "code": code},
                         ensure_ascii=False))
    else:
        sys.stderr.write(f"[ERROR] ({code}) {msg}"
                         + (f"  step={step}" if step else "") + "\n")


def emit_result(summary: dict, json_out: bool):
    if json_out:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        line = summary.get("human")
        if line:
            print(line)


def summarize_import(counters: dict) -> str:
    parts = [
        f"新增 {counters.get('added', counters.get('inserted', 0))}",
        f"覆盖 {counters.get('overwritten', counters.get('updated', 0))}",
        f"跳过 {counters.get('skipped', 0)}",
        f"失败 {counters.get('failed', 0)}",
    ]
    if 'intra_dup' in counters:
        parts.append(f"批内重复 {counters['intra_dup']}")
    if 'loaded' in counters and 'expected' in counters:
        ok = '✓' if counters.get('reconciled') else '✗'
        parts.append(f"已装载 {counters['loaded']}/期望 {counters['expected']} 一致{ok}")
    return "  ".join(parts)


# ---------------------------------------------------------------------------
# 公共：CSV 表头定位与别名映射
# ---------------------------------------------------------------------------
def map_header(header, alias_map, required):
    """根据别名表把表头单元格映射到字段名，返回 {field: index}。"""
    idx = {}
    norm = {str(h).strip(): i for i, h in enumerate(header)}
    for field, aliases in alias_map.items():
        for a in aliases:
            if a in norm:
                idx[field] = norm[a]
                break
    missing = [f for f in required if f not in idx]
    if missing:
        raise CliError(EXIT_PARAM, f"表头缺少必填列: {missing}", "header")
    return idx


def locate_header_row(rows, marker='bk_property_id'):
    """属性导入：定位首单元格为 marker 的行为表头。"""
    for i, row in enumerate(rows):
        if row and str(row[0]).strip() == marker:
            return i
    raise CliError(EXIT_PARAM, f"未找到表头行（首单元格应为 {marker}）", "header")


# ---------------------------------------------------------------------------
# 核心：分类
# ---------------------------------------------------------------------------
def create_classification_core(c, cid, cname, icon, ispre, on_dup, dry_run):
    if dry_run:
        existing = c.query_one(
            "SELECT 1 FROM cc_ObjClassification WHERE bk_classification_id=:cid",
            {"cid": cid})
        action = 'create' if not existing else ('overwrite' if on_dup != 'skip' else 'skip')
        print(f"[dry-run] 分类 {cid}: {action}")
        return {'action': action}
    # 依赖调用方事务（cmd_* / do_*_import 负责开启）
    existing = c.query_one(
        "SELECT 1 FROM cc_ObjClassification WHERE bk_classification_id=:cid",
        {"cid": cid})
    if existing:
        if on_dup == 'error':
            raise CliError(EXIT_EXISTS, f"分类已存在: {cid}", "dup_check")
        if on_dup == 'skip':
            return {'action': 'skip'}
        c.exec(
            "UPDATE cc_ObjClassification SET bk_classification_name=:n, "
            "bk_classification_icon=:i, ispre=:p WHERE bk_classification_id=:cid",
            {"n": cname, "i": icon, "p": ispre, "cid": cid})
        return {'action': 'overwrite'}
    c.exec(
        "INSERT INTO cc_ObjClassification "
        "(id, bk_classification_id, bk_classification_name, bk_classification_icon, "
        "ispre, bk_supplier_account) VALUES "
        "(:id, :bk_classification_id, :bk_classification_name, :bk_classification_icon, "
        ":ispre, '0')",
        {"id": generate_id(), "bk_classification_id": cid, "bk_classification_name": cname,
         "bk_classification_icon": icon, "ispre": ispre})
    return {'action': 'create'}


# ---------------------------------------------------------------------------
# 核心：模型（含分组 / 系统属性 / 实例表 / 关联表 / 默认唯一约束）
# ---------------------------------------------------------------------------
def _sys_attr_params(oid, sp):
    return {
        "_id": f"{oid}.{sp['bk_property_id']}",
        "id": generate_id(),
        "bk_obj_id": oid,
        "bk_property_id": sp['bk_property_id'],
        "bk_property_name": sp['bk_property_name'],
        "bk_property_type": sp['bk_property_type'],
        "bk_property_group": sp['bk_property_group'],
        "isrequired": sp['isrequired'],
        "bk_ispassword": sp['bk_ispassword'],
        "bk_ishidden": sp['bk_ishidden'],
        "isreadonly": sp['isreadonly'],
        "isonly": sp.get('isonly', 0),
        "bk_isapi": sp['bk_isapi'],
        "bk_issystem": sp['bk_issystem'],
        "ispre": sp['ispre'],
        "bk_property_index": sp['bk_property_index'],
        "unit": sp.get('unit', ''),
        "placeholder": sp.get('placeholder', ''),
        "editable": sp['editable'],
        "option": sp.get('option'),
        "bk_supplier_account": dbmod.SUPPLIER,
    }


def create_model_core(c, o, dry_run):
    oid = o['bk_obj_id']
    validate_identifier(oid)
    if dry_run:
        print(f"[dry-run] CREATE MODEL {oid} (group+4系统属性+2分表+唯一约束)")
        return {'action': 'create'}
    warning = None
    # 依赖调用方事务（cmd_* / do_*_import 负责开启）
    if not c.query_one(
            "SELECT 1 FROM cc_ObjClassification WHERE bk_classification_id=:cid",
            {"cid": o['bk_classification_id']}):
        raise CliError(EXIT_DEP, f"分类不存在: {o['bk_classification_id']}",
                       "check_classification")
    existing = c.query_one("SELECT 1 FROM cc_ObjDes WHERE bk_obj_id=:oid", {"oid": oid})
    if existing:
        if o['on_dup'] == 'error':
            raise CliError(EXIT_EXISTS, f"模型已存在: {oid}", "dup_check")
        if o['on_dup'] == 'skip':
            return {'action': 'skip'}
        c.exec(
            "UPDATE cc_ObjDes SET bk_obj_name=:n, bk_obj_icon=:i, ispre=:p, "
            "bk_ishidden=:h, bk_ispaused=:pa, obj_sort_number=:s "
            "WHERE bk_obj_id=:oid",
            {"n": o['bk_obj_name'], "i": o['bk_obj_icon'], "p": o['ispre'],
             "h": o['bk_ishidden'], "pa": o['bk_ispaused'], "s": o['obj_sort_number'],
             "oid": oid})
        return {'action': 'overwrite'}

    dbmod.ensure_object_unique_table(c)
    # 1) 模型元数据
    c.exec(
        "INSERT INTO cc_ObjDes "
        "(_id, id, bk_obj_id, bk_obj_name, bk_obj_icon, bk_classification_id, "
        "ispre, bk_ishidden, bk_ispaused, obj_sort_number, creator, modifier, "
        "bk_supplier_account) VALUES "
        "(:_id, :id, :bk_obj_id, :bk_obj_name, :bk_obj_icon, :bk_classification_id, "
        ":ispre, :bk_ishidden, :bk_ispaused, :obj_sort_number, 'admin', 'admin', '0')",
        {"_id": oid, "id": generate_id(), "bk_obj_id": oid,
         "bk_obj_name": o['bk_obj_name'], "bk_obj_icon": o['bk_obj_icon'],
         "bk_classification_id": o['bk_classification_id'], "ispre": o['ispre'],
         "bk_ishidden": o['bk_ishidden'], "bk_ispaused": o['bk_ispaused'],
         "obj_sort_number": o['obj_sort_number']})
    # 2) 默认分组（对齐上游 logics/model/object.go:147-154 创建自定义模型时的 default 分组：
    #    GroupID = NewGroupID(true) = "default"（小写ID）、IsDefault = true、GroupIndex = -1；
    #    显示名上游硬编码英文 "Default"，此处取中文语境的标准名「基础信息」
    #    （admin_server/common/definitions.go:22 BaseInfoName，亦为上游 UI 中文 i18n 值）
    c.exec(
        "INSERT INTO cc_PropertyGroup "
        "(_id, id, bk_obj_id, bk_group_id, bk_group_name, bk_group_index, "
        "bk_isdefault, is_collapse, ispre, bk_biz_id, creator, modifier, "
        "bk_supplier_account) VALUES "
        "(:_id, :id, :bk_obj_id, 'default', '基础信息', -1, true, false, true, 0, "
        "'admin', 'admin', '0')",
        {"_id": f"{oid}.default", "id": generate_id(), "bk_obj_id": oid})
    # 3) 4 个系统属性（逐行独立 generate_id，C2）
    for sp in SYSTEM_PROPERTIES:
        c.exec(
            "INSERT INTO cc_ObjAttDes (" + ", ".join(SYS_ATTR_COLS) + ") VALUES ("
            + ", ".join(f":{col}" for col in SYS_ATTR_COLS) + ")",
            _sys_attr_params(oid, sp))
    # 4) 实例分表 + 关联分表
    c.exec(INSTANCE_TABLE_DDL.format(tbl=quote_ident_raw(dbmod.instance_table(oid))))
    c.exec(ASSOC_TABLE_DDL.format(tbl=quote_ident_raw(dbmod.assoc_table(oid))))
    # 5) 默认唯一约束（C3，以 --unique-by 默认 bk_inst_name）
    if o['with_tables'] and o['unique_by']:
        key_attr = c.query_one(
            "SELECT id FROM cc_ObjAttDes WHERE bk_obj_id=:o AND bk_property_id=:p",
            {"o": oid, "p": o['unique_by']})
        if key_attr:
            keys = json.dumps(
                [{"key_kind": "property", "key_id": key_attr['id']}],
                ensure_ascii=False)
            c.exec(
                "INSERT OR REPLACE INTO cc_ObjectUnique "
                "(_id, id, bk_obj_id, keys, ispre, bk_supplier_account) VALUES "
                "(:_id, :id, :bk_obj_id, :keys, 1, '0')",
                {"_id": f"{oid}_{o['unique_by']}", "id": generate_id(),
                 "bk_obj_id": oid, "keys": keys})
        else:
            warning = (f"唯一约束键属性 '{o['unique_by']}' 不存在，"
                       f"跳过 cc_ObjectUnique 写入（该模型实例导入将退为纯 INSERT）")
    return {'action': 'create', 'warning': warning}


# ---------------------------------------------------------------------------
# 核心：属性（定义 + ALTER 实例表加列）
# ---------------------------------------------------------------------------
def _normalize_option(ptype, option_raw):
    if ptype not in ('enum', 'enummulti', 'list') or not option_raw:
        return None
    opt = parse_json(option_raw)
    if opt is None:
        raise CliError(EXIT_PARAM, f"option 非法 JSON: {option_raw}", "option")
    if isinstance(opt, list) and opt and isinstance(opt[0], str):
        return convert_enum_option(opt)
    return json.dumps(opt, ensure_ascii=False)


def add_attribute_core(c, oid, p, dry_run, on_dup='error'):
    validate_identifier(oid)
    validate_identifier(p['bk_property_id'])
    if dry_run:
        print(f"[dry-run] ADD ATTR {oid}.{p['bk_property_id']} + ALTER TABLE")
        return {'action': 'create'}
    # 联动规则（对齐上游 bk-cmdb）：isonly=true 时强制 isrequired=true
    if p.get('isonly'):
        p['isrequired'] = True
    # 空值兜底（对齐上游 checkAttributeGroupExist）：未指定分组时落 'default'（小写）
    # 注意：'default' 是 bk_group_id（分组ID），不是显示名；上游 NewGroupID(true) 返回小写 "default"
    if not (p.get('bk_property_group') or '').strip():
        p['bk_property_group'] = 'default'
    # 依赖调用方事务（cmd_attribute_create / do_attribute_import / cmd_scaffold_spec 负责开启）
    if not c.query_one("SELECT 1 FROM cc_ObjDes WHERE bk_obj_id=:o", {"o": oid}):
        raise CliError(EXIT_DEP, f"模型不存在: {oid}", "check_model")
    existing = c.query_one(
        "SELECT 1 FROM cc_ObjAttDes WHERE bk_obj_id=:o AND bk_property_id=:pid",
        {"o": oid, "pid": p['bk_property_id']})
    if existing:
        if on_dup == 'error':
            raise CliError(EXIT_EXISTS, f"属性已存在: {oid}.{p['bk_property_id']}",
                           "dup_check")
        if on_dup == 'skip':
            return {'action': 'skip'}
        c.exec(
            "UPDATE cc_ObjAttDes SET bk_property_name=:n, bk_property_type=:t, "
            "bk_property_group=:g, isrequired=:r, editable=:e, bk_ishidden=:h, "
            "bk_isapi=:a, bk_issystem=:s, ispre=:p, ismultiple=:m, bk_property_index=:i, "
            "option=:o, placeholder=:ph, unit=:u, isreadonly=:ro, isonly=:io "
            "WHERE bk_obj_id=:oid AND bk_property_id=:pid",
            {"n": p['bk_property_name'], "t": p['bk_property_type'], "g": p['bk_property_group'],
             "r": p['isrequired'], "e": p['editable'], "h": p['bk_ishidden'], "a": p['bk_isapi'],
             "s": p['bk_issystem'], "p": p['ispre'], "m": p['ismultiple'],
             "i": p['bk_property_index'], "o": p['option'], "ph": p['placeholder'],
             "u": p['unit'], "ro": p.get('isreadonly', 0), "io": p.get('isonly', 0),
             "oid": oid, "pid": p['bk_property_id']})
        return {'action': 'overwrite'}

    sql_type = get_sql_type(p['bk_property_type'])
    params = {
        "_id": f"{oid}.{p['bk_property_id']}",
        "id": generate_id(),
        "bk_obj_id": oid,
        "bk_property_id": p['bk_property_id'],
        "bk_property_name": p['bk_property_name'],
        "bk_property_type": p['bk_property_type'],
        "bk_property_group": p['bk_property_group'],
        "isrequired": p['isrequired'],
        "bk_ispassword": 0,
        "bk_ishidden": p['bk_ishidden'],
        "isreadonly": p.get('isreadonly', 0),
        "isonly": p.get('isonly', 0),
        "bk_isapi": p['bk_isapi'],
        "bk_issystem": p['bk_issystem'],
        "ispre": p['ispre'],
        "ismultiple": p['ismultiple'],
        "bk_property_index": p['bk_property_index'],
        "option": p['option'],
        "placeholder": p['placeholder'],
        "unit": p['unit'],
        "editable": p['editable'],
        "bk_supplier_account": dbmod.SUPPLIER,
    }
    c.exec(
        "INSERT INTO cc_ObjAttDes (" + ", ".join(ATTR_COLS) + ") VALUES ("
        + ", ".join(f":{col}" for col in ATTR_COLS) + ")",
        params)
    # ALTER 实例表加列（M5：先探测已存在列则跳过）
    tbl = dbmod.instance_table(oid)
    cols = [r['name'] for r in c.query_all(f"PRAGMA table_info({quote_ident_raw(tbl)})")]
    if p['bk_property_id'] not in cols:
        c.exec(
            f"ALTER TABLE {quote_ident_raw(tbl)} ADD COLUMN "
            f"{quote_ident(p['bk_property_id'])} {sql_type}")
    return {'action': 'create'}


# ===========================================================================
# 导入核心（复用自上游命令；支持外部连接 / 事务，供 scaffold apply 串联）
# ===========================================================================
def do_classification_import(c, csv_path, opts, dry_run, skip_empty=False):
    rows = read_csv_rows(csv_path, opts.get('encoding', 'utf-8-sig'),
                         opts.get('delimiter', ','))
    if len(rows) < 1:
        raise CliError(EXIT_PARAM, "CSV 为空", "empty")
    header = rows[0]
    data = rows[1:]
    if len(data) == 0:
        if skip_empty:
            return {'added': 0, 'overwritten': 0, 'skipped': 0, 'failed': 0,
                    'human': '分类导入：无数据行，跳过'}
        raise CliError(EXIT_PARAM, "分类 CSV 无数据行（预检失败）", "preflight")
    idx = map_header(header, {
        'bk_classification_id': ['bk_classification_id', '分类id', '分类ID'],
        'bk_classification_name': ['bk_classification_name', '分类名称'],
        'bk_classification_icon': ['bk_classification_icon', '图标'],
        'ispre': ['ispre', '是否预置'],
    }, required=['bk_classification_id', 'bk_classification_name'])
    added = skipped = overwritten = failed = 0
    on_dup = opts.get('on_dup', 'overwrite')
    with c.conn.begin():
        for i, row in enumerate(data, start=2):
            cid = (row[idx['bk_classification_id']].strip()
                   if idx['bk_classification_id'] < len(row) else '')
            cname = (row[idx['bk_classification_name']].strip()
                     if idx['bk_classification_name'] < len(row) else '')
            icon = (row[idx['bk_classification_icon']].strip()
                    if 'bk_classification_icon' in idx and idx['bk_classification_icon'] < len(row)
                    else '') or 'icon-cc-default'
            if not cid or not cname:
                failed += 1
                continue
            try:
                # ispre 解析置于行级 try 内，使非布尔值经 ValueError 被捕获并计入失败行，
                # 而非穿透循环导致整份 CSV 回滚（与 model/attribute/instance 导入一致）
                ispre = False
                if 'ispre' in idx and idx['ispre'] < len(row) and row[idx['ispre']].strip():
                    ispre = parse_bool(row[idx['ispre']])
                r = create_classification_core(c, cid, cname, icon, ispre, on_dup, dry_run)
                if r['action'] == 'create':
                    added += 1
                elif r['action'] == 'overwrite':
                    overwritten += 1
                else:
                    skipped += 1
            except (CliError, ValueError, TypeError) as e:
                if opts.get('strict'):
                    raise
                failed += 1
    return {'added': added, 'overwritten': overwritten, 'skipped': skipped,
            'failed': failed, 'human': f"分类导入：{summarize_import(locals())}"}


def do_model_import(c, csv_path, opts, dry_run, skip_empty=False):
    rows = read_csv_rows(csv_path, opts.get('encoding', 'utf-8-sig'),
                         opts.get('delimiter', ','))
    if len(rows) < 1:
        raise CliError(EXIT_PARAM, "CSV 为空", "empty")
    header = rows[0]
    data = rows[1:]
    if len(data) == 0:
        if skip_empty:
            return {'added': 0, 'overwritten': 0, 'skipped': 0, 'failed': 0,
                    'human': '模型导入：无数据行，跳过'}
        raise CliError(EXIT_PARAM, "模型 CSV 无数据行（预检失败）", "preflight")
    idx = map_header(header, {
        'bk_obj_id': ['bk_obj_id', '模型id', '模型ID'],
        'bk_obj_name': ['bk_obj_name', '模型名称'],
        'bk_classification_id': ['bk_classification_id', '所属分类', '分类id', '分类ID'],
        'bk_obj_icon': ['bk_obj_icon', '模型图标', '图标'],
        'ispre': ['ispre', '是否预置'],
        'bk_ishidden': ['bk_ishidden', '是否隐藏'],
        'bk_ispaused': ['bk_ispaused', '是否停用'],
        'obj_sort_number': ['obj_sort_number', '排序号', '排序'],
    }, required=['bk_obj_id', 'bk_obj_name', 'bk_classification_id'])
    added = skipped = overwritten = failed = 0
    on_dup = opts.get('on_dup', 'overwrite')
    with_sys = opts.get('with_system_props', True)
    with_tbl = opts.get('with_tables', True)
    unique_by = opts.get('unique_by', 'bk_inst_name')
    with c.conn.begin():
        for i, row in enumerate(data, start=2):
            def cell(f):
                ci = idx.get(f)
                if ci is None or ci >= len(row):
                    return ''
                return row[ci].strip()
            oid = cell('bk_obj_id')
            if not oid:
                failed += 1
                continue
            try:
                validate_identifier(oid)
                o = {
                    'bk_obj_id': oid,
                    'bk_obj_name': cell('bk_obj_name'),
                    'bk_classification_id': cell('bk_classification_id'),
                    'bk_obj_icon': cell('bk_obj_icon') or 'icon-cc-default',
                    'ispre': parse_bool(cell('ispre')) if cell('ispre') else False,
                    'bk_ishidden': parse_bool(cell('bk_ishidden')) if cell('bk_ishidden') else False,
                    'bk_ispaused': parse_bool(cell('bk_ispaused')) if cell('bk_ispaused') else False,
                    'obj_sort_number': int(cell('obj_sort_number')) if cell('obj_sort_number') else 0,
                    'with_system_props': with_sys,
                    'with_tables': with_tbl,
                    'unique_by': unique_by,
                    'on_dup': on_dup,
                }
                r = create_model_core(c, o, dry_run)
                if r['action'] == 'create':
                    added += 1
                elif r['action'] == 'overwrite':
                    overwritten += 1
                else:
                    skipped += 1
                if r.get('warning'):
                    sys.stderr.write(f"[WARN] {r['warning']}\n")
            except (CliError, InvalidIdentifierError, ValueError, TypeError) as e:
                if opts.get('strict'):
                    raise
                failed += 1
    return {'added': added, 'overwritten': overwritten, 'skipped': skipped,
            'failed': failed, 'human': f"模型导入：{summarize_import(locals())}"}


def do_attribute_import(c, csv_path, opts, dry_run, skip_empty=False):
    oid = opts['bk_obj_id']
    validate_identifier(oid)
    # 整段在调用方事务内（cmd_attribute_import / scaffold apply 已开启）；
    # 此处显式 begin 以确保写入提交，并避免前置 SELECT 的隐式事务与核心写入冲突
    with c.conn.begin():
        if not c.query_one("SELECT 1 FROM cc_ObjDes WHERE bk_obj_id=:o", {"o": oid}):
            raise CliError(EXIT_DEP, f"模型不存在: {oid}", "check_model")
        rows = read_csv_rows(csv_path, opts.get('encoding', 'utf-8-sig'),
                             opts.get('delimiter', ','))
        if len(rows) < 1:
            raise CliError(EXIT_PARAM, "CSV 为空", "empty")
        hidx = locate_header_row(rows, 'bk_property_id')
        header = rows[hidx]
        data = rows[hidx + 1:]
        if len(data) == 0:
            if skip_empty:
                return {'added': 0, 'overwritten': 0, 'skipped': 0, 'failed': 0,
                        'description_dropped': 0,
                        'human': f'属性导入 {oid}：无数据行，跳过'}
            raise CliError(EXIT_PARAM, "属性 CSV 无数据行（预检失败）", "preflight")
        # 预检画像（H1）
        prof = profile_source(header, data)
        if opts.get('verbose'):
            print(f"[preflight] 属性导入 {oid}: 数据行={prof['data_rows']} 列={prof['columns']}")
        # 列索引
        colpos = {h.strip(): i for i, h in enumerate(header)}
        need = ['bk_property_id', 'bk_property_name', 'bk_property_type']
        missing = [x for x in need if x not in colpos]
        if missing:
            raise CliError(EXIT_PARAM, f"属性表头缺少必填列: {missing}", "header")
        added = skipped = overwritten = failed = desc_dropped = 0
        on_dup = opts.get('on_dup', 'overwrite')
        for i, row in enumerate(data, start=hidx + 2):
            def cell(f):
                ci = colpos.get(f)
                if ci is None or ci >= len(row):
                    return ''
                return row[ci].strip()
            pid = cell('bk_property_id')
            pname = cell('bk_property_name')
            ptype = cell('bk_property_type')
            if not pid or not pname or not ptype:
                failed += 1
                continue
            try:
                if ptype not in VALID_PROPERTY_TYPES:
                    raise CliError(EXIT_PARAM, f"非法 bk_property_type: {ptype}", "type")
                # 分组解析（D 列按分组名/ID 解析）
                grp = cell('bk_property_group') or 'default'
                grp_row = c.query_one(
                    "SELECT bk_group_id FROM cc_PropertyGroup WHERE bk_obj_id=:o "
                    "AND (bk_group_id=:g OR bk_group_name=:g)",
                    {"o": oid, "g": grp})
                if grp_row:
                    bk_group_id = grp_row['bk_group_id']
                elif opts.get('group_auto_create'):
                    validate_identifier(grp)
                    c.exec(
                        "INSERT INTO cc_PropertyGroup "
                        "(_id, id, bk_obj_id, bk_group_id, bk_group_name, bk_group_index, "
                        "bk_isdefault, is_collapse, ispre, bk_biz_id, creator, modifier, "
                        "bk_supplier_account) VALUES "
                        "(:_id, :id, :bk_obj_id, :bk_group_id, :bk_group_name, 0, false, false, "
                        "true, 0, 'admin', 'admin', '0')",
                        {"_id": f"{oid}.{grp}", "id": generate_id(), "bk_obj_id": oid,
                         "bk_group_id": grp,
                         "bk_group_name": KNOWN_GROUP_NAMES.get(grp, grp)})
                    bk_group_id = grp
                else:
                    bk_group_id = 'default'
                # option 归一
                option_raw = cell('option')
                option_json = _normalize_option(ptype, option_raw) if option_raw else None
                # G 列 description：lite 未实现，默认丢弃并告警（§5.7.1）
                if 'description' in colpos and colpos['description'] < len(row) \
                        and row[colpos['description']].strip():
                    desc_dropped += 1
                p = {
                    'bk_property_id': pid,
                    'bk_property_name': pname,
                    'bk_property_type': ptype,
                    'bk_property_group': bk_group_id,
                    'isrequired': parse_bool(cell('isrequired')) if cell('isrequired') else False,
                    'editable': parse_bool(cell('editable')) if cell('editable') else True,
                    'bk_ishidden': parse_bool(cell('bk_ishidden')) if cell('bk_ishidden') else False,
                    'bk_isapi': parse_bool(cell('bk_isapi')) if cell('bk_isapi') else False,
                    'bk_issystem': parse_bool(cell('bk_issystem')) if cell('bk_issystem') else False,
                    'ispre': parse_bool(cell('ispre')) if cell('ispre') else False,
                    'isreadonly': parse_bool(cell('isreadonly')) if cell('isreadonly') else False,
                    'isonly': parse_bool(cell('isonly')) if cell('isonly') else False,
                    'ismultiple': parse_bool(cell('ismultiple')) if cell('ismultiple') else False,
                    'bk_property_index': int(cell('bk_property_index')) if cell('bk_property_index') else 0,
                    'option': option_json,
                    'placeholder': cell('placeholder'),
                    'unit': cell('unit'),
                }
                r = add_attribute_core(c, oid, p, dry_run, on_dup=on_dup)
                if r['action'] == 'create':
                    added += 1
                elif r['action'] == 'overwrite':
                    overwritten += 1
                else:
                    skipped += 1
            except (CliError, InvalidIdentifierError, ValueError, TypeError) as e:
                if opts.get('strict'):
                    raise
                failed += 1
        if desc_dropped:
            sys.stderr.write(f"[WARN] 已丢弃 {desc_dropped} 行 description 列（lite 未实现）\n")
    return {'added': added, 'overwritten': overwritten, 'skipped': skipped,
            'failed': failed, 'description_dropped': desc_dropped,
            'human': f"属性导入 {oid}：{summarize_import(locals())}"}


def do_instance_import(c, csv_path, opts, dry_run, skip_empty=False):
    oid = opts['bk_obj_id']
    validate_identifier(oid)
    tbl = dbmod.instance_table(oid)
    if not c.query_one("SELECT 1 FROM cc_ObjDes WHERE bk_obj_id=:o", {"o": oid}):
        raise CliError(EXIT_DEP, f"模型不存在: {oid}", "check_model")
    if not dbmod.table_exists(c, tbl):
        raise CliError(EXIT_DEP, f"实例表不存在: {tbl}（请先 model create 或 table create）",
                       "check_table")
    attrs = c.query_all(
        "SELECT id, bk_property_id, bk_property_type, option FROM cc_ObjAttDes "
        "WHERE bk_obj_id=:o AND bk_property_id NOT IN ('id','bk_inst_id','bk_obj_id') "
        "AND bk_isapi=0 AND bk_ishidden=0", {"o": oid})
    attr_by_pid = {a['bk_property_id']: a for a in attrs}
    id_to_pid = {a['id']: a['bk_property_id'] for a in attrs}
    allowed = {'bk_inst_name', 'bk_inst_id'} | set(attr_by_pid.keys())

    rows = read_csv_rows(csv_path, opts.get('encoding', 'utf-8-sig'),
                         opts.get('delimiter', ','))
    if len(rows) < 1:
        raise CliError(EXIT_PARAM, "CSV 为空", "empty")
    header = rows[0]
    data = rows[1:]
    if len(data) == 0:
        if skip_empty:
            return {'inserted': 0, 'updated': 0, 'skipped': 0, 'failed': 0,
                    'intra_dup': 0, 'expected': 0, 'loaded': 0, 'reconciled': True,
                    'human': f'实例导入 {oid}：无数据行，跳过'}
        raise CliError(EXIT_PARAM, "实例 CSV 无数据行（预检失败）", "preflight")

    # 预检画像（H1）+ 表头预检（§5.11.2）
    prof = profile_source(header, data)
    if opts.get('verbose'):
        print(f"[preflight] 实例导入 {oid}: 数据行={prof['data_rows']} 列={prof['columns']} 样本={prof['sample']}")
    hdr_idx = {h.strip(): i for i, h in enumerate(header)}
    unknown = [h for h in hdr_idx if h not in allowed]
    if unknown:
        if opts.get('skip_unknown_columns'):
            for u in unknown:
                del hdr_idx[u]
        else:
            raise CliError(EXIT_PARAM, f"表头含未知列（不在实例表允许写入列集）: {unknown}",
                           "preflight")
    if 'bk_inst_name' not in hdr_idx:
        raise CliError(EXIT_PARAM, "表头缺少必填列 bk_inst_name", "preflight")

    # 判定模式（auto/insert/upsert）+ 匹配键
    mode = opts.get('mode', 'auto')
    match_cols = None
    if mode != 'insert':
        if opts.get('upsert_key'):
            match_cols = [v.strip() for v in opts['upsert_key'].split(',') if v.strip()]
            for mc in match_cols:
                validate_identifier(mc)
        elif mode == 'upsert' or mode == 'auto':
            uniq_rows = c.query_all("SELECT keys FROM cc_ObjectUnique WHERE bk_obj_id=:o",
                                    {"o": oid})
            keys_set = set()
            for ur in uniq_rows:
                for k in (parse_json(ur['keys']) or []):
                    pid = id_to_pid.get(k.get('key_id'))
                    if pid:
                        keys_set.add(pid)
            match_cols = list(keys_set) if keys_set else None
            if mode == 'upsert' and not match_cols:
                raise CliError(EXIT_PARAM, "upsert 模式但无唯一约束可判定，请用 --upsert-key",
                               "resolve_keys")
    # auto 且无唯一约束 → insert 模式
    effective_mode = 'upsert' if match_cols else 'insert'
    # 预检（§5.11.14）：由 cc_ObjectUnique 解析出的匹配列必须全部出现在 CSV 表头内，
    # 否则逐行构造 WHERE k=:v 时 values[k] 会 KeyError（仅手工改库设非 bk_inst_name
    # 唯一键时才可能触发）；缺列即清晰报错退出码 2，而非落下通用异常 1。
    if match_cols:
        missing = [mc for mc in match_cols if mc not in hdr_idx]
        if missing:
            raise CliError(EXIT_PARAM,
                           f"匹配键列不在 CSV 表头中: {missing}", "preflight")
    if opts.get('verbose'):
        print(f"[mode] {effective_mode} 匹配键={match_cols}")

    if dry_run:
        print(f"[dry-run] 实例导入 {oid}: 模式={effective_mode} 匹配键={match_cols} 数据行={len(data)}")
        return {'inserted': 0, 'updated': 0, 'skipped': 0, 'failed': 0,
                'intra_dup': 0, 'expected': len(data), 'loaded': 0, 'reconciled': True,
                'human': f'实例导入(预演) {oid}：模式={effective_mode} 行={len(data)}'}

    atomic = opts.get('atomic', True)
    batch_size = opts.get('batch_size', 500)
    enum_by_name = opts.get('enum_by_name', False)
    mv_sep = opts.get('multivalue_sep', ',')
    strict = opts.get('strict', False)
    generate_inst_id = opts.get('generate_inst_id', True)

    inserted = updated = skipped = failed = intra_dup = 0
    seen_keys = set()
    reject = RejectStore(csv_path, opts.get('reject_out'))

    def build_write(values):
        write = {'bk_obj_id': oid, 'bk_supplier_account': dbmod.SUPPLIER}
        inst_id = values.get('bk_inst_id') if values.get('bk_inst_id') not in (None, '') else None
        if inst_id is None and generate_inst_id:
            inst_id = generate_id()
        write['bk_inst_id'] = inst_id
        write['id'] = inst_id
        write['bk_inst_name'] = values.get('bk_inst_name')
        for col, v in values.items():
            if col in ('bk_inst_name', 'bk_inst_id'):
                continue
            write[col] = v
        return write

    def do_row(values):
        nonlocal inserted, updated
        if effective_mode == 'upsert':
            where = {k: values[k] for k in match_cols}
            placeholders = " AND ".join(f"{quote_ident(k)}=:wk_{k}" for k in match_cols)
            params = {f"wk_{k}": where[k] for k in match_cols}
            hit = c.query_one(
                f"SELECT 1 FROM {quote_ident_raw(tbl)} WHERE {placeholders}", params)
            if hit:
                set_cols = [col for col in values if col not in UPDATE_EXCLUDE]
                if set_cols:
                    set_clause = ", ".join(f"{quote_ident(col)}=:{col}" for col in set_cols)
                    up = {col: values[col] for col in set_cols}
                    c.exec(f"UPDATE {quote_ident_raw(tbl)} SET {set_clause} "
                           f"WHERE {placeholders}", {**up, **params})
                updated += 1
            else:
                write = build_write(values)
                cols = list(write.keys())
                c.exec(
                    f"INSERT INTO {quote_ident_raw(tbl)} ("
                    + ", ".join(quote_ident(col) for col in cols) + ") VALUES ("
                    + ", ".join(f":{col}" for col in cols) + ")", write)
                inserted += 1
        else:
            write = build_write(values)
            cols = list(write.keys())
            c.exec(
                f"INSERT INTO {quote_ident_raw(tbl)} ("
                + ", ".join(quote_ident(col) for col in cols) + ") VALUES ("
                + ", ".join(f":{col}" for col in cols) + ")", write)
            inserted += 1

    for ln, row in enumerate(data, start=2):
        values = {}
        try:
            for col, ci in hdr_idx.items():
                raw = row[ci].strip() if ci < len(row) else ''
                if col == 'bk_inst_id':
                    v = int(raw) if raw else None
                elif col == 'bk_inst_name':
                    v = raw
                else:
                    attr = attr_by_pid.get(col)
                    v, err = coerce_value(raw, attr['bk_property_type'],
                                         parse_json(attr['option']) if attr.get('option') else None,
                                         enum_by_name, mv_sep)
                    if err:
                        raise CliError(EXIT_PARAM, err, "coerce")
                values[col] = v
            if not values.get('bk_inst_name'):
                raise CliError(EXIT_PARAM, "实例名称必填缺失", "required")
            # 批内主键重复（H2）
            if match_cols:
                key = tuple(values.get(k) for k in match_cols)
                if key in seen_keys:
                    if strict:
                        raise CliError(EXIT_GENERAL, f"批内重复键: {key}", "intra_dup")
                    reject.add(ln, row, ",".join(match_cols), "批内重复键")
                    intra_dup += 1
                    continue
                seen_keys.add(key)
            do_row(values)
        except (CliError, InvalidIdentifierError, ValueError) as e:
            if strict:
                reject.flush()
                raise
            reject.add(ln, row, getattr(e, 'step', '') or '', str(e))
            failed += 1
        # 非原子模式按批提交
        if not atomic and (ln % batch_size == 0):
            c.commit()
    if not atomic:
        c.commit()

    reject.flush()
    # 装载血缘（M1，best-effort）
    try:
        dbmod.ensure_import_batch_table(c)
        batch_id = opts.get('batch_id') or f"cli/{int(time.time())}"
        c.exec(
            "INSERT INTO cc_ImportBatch (_id, batch_id, source_file, bk_obj_id, "
            "row_count, reject_count) VALUES (:_id, :batch_id, :src, :oid, :rc, :rjc)",
            {"_id": f"{batch_id}_{oid}", "batch_id": batch_id, "src": os.path.basename(csv_path),
             "oid": oid, "rc": inserted + updated, "rjc": reject.count})
        if not atomic:
            c.commit()
    except Exception:  # noqa: BLE001
        pass

    expected = len(data) - failed - skipped - intra_dup
    loaded = inserted + updated
    reconciled = (loaded == expected)
    if not reconciled and strict:
        raise CliError(EXIT_GENERAL, f"对账不一致：已装载 {loaded} / 期望 {expected}",
                       "reconcile")
    return {'inserted': inserted, 'updated': updated, 'skipped': skipped,
            'failed': failed, 'intra_dup': intra_dup, 'expected': expected,
            'loaded': loaded, 'reconciled': reconciled,
            'human': f"实例导入 {oid}：{summarize_import(locals())}"}


# ===========================================================================
# 子命令处理器
# ===========================================================================
def cmd_classification_create(args):
    with dbmod.cli_conn() as c:
        with c.conn.begin():
            r = create_classification_core(
                c, args.bk_classification_id, args.bk_classification_name,
                args.bk_classification_icon, args.ispre, args.on_duplicate, args.dry_run)
    emit_result({**r, 'human': f"分类 {args.bk_classification_id}: {r['action']}"}, args.json)
    return EXIT_OK


def cmd_model_create(args):
    o = {
        'bk_obj_id': args.bk_obj_id,
        'bk_obj_name': args.bk_obj_name,
        'bk_classification_id': args.bk_classification_id,
        'bk_obj_icon': args.bk_obj_icon,
        'ispre': args.ispre,
        'bk_ishidden': False,
        'bk_ispaused': False,
        'obj_sort_number': args.obj_sort_number,
        'with_system_props': args.with_system_props,
        'with_tables': args.with_tables,
        'unique_by': args.unique_by,
        'on_dup': args.on_duplicate,
    }
    with dbmod.cli_conn() as c:
        with c.conn.begin():
            r = create_model_core(c, o, args.dry_run)
    if r.get('warning'):
        sys.stderr.write(f"[WARN] {r['warning']}\n")
    emit_result({**r, 'human': f"模型 {args.bk_obj_id}: {r['action']}"}, args.json)
    return EXIT_OK


def cmd_attribute_create(args):
    p = {
        'bk_property_id': args.bk_property_id,
        'bk_property_name': args.bk_property_name,
        'bk_property_type': args.bk_property_type,
        'bk_property_group': args.bk_property_group,
        'isrequired': args.isrequired,
        'editable': args.editable,
        'bk_ishidden': args.bk_ishidden,
        'bk_isapi': args.bk_isapi,
        'bk_issystem': args.bk_issystem,
        'ispre': args.ispre,
        'ismultiple': args.ismultiple,
        'bk_property_index': args.bk_property_index,
        'option': _normalize_option(args.bk_property_type, args.option) if args.option else None,
        'placeholder': args.placeholder or '',
        'unit': args.unit or '',
    }
    with dbmod.cli_conn() as c:
        with c.conn.begin():
            r = add_attribute_core(c, args.bk_obj_id, p, args.dry_run, on_dup=args.on_duplicate)
    emit_result({**r, 'human': f"属性 {args.bk_obj_id}.{args.bk_property_id}: {r['action']}"},
                args.json)
    return EXIT_OK


def cmd_table_create(args):
    oid = args.bk_obj_id
    validate_identifier(oid)
    with dbmod.cli_conn() as c:
        if args.dry_run:
            print(f"[dry-run] CREATE TABLE {dbmod.instance_table(oid)} + {dbmod.assoc_table(oid)}")
            return EXIT_OK
        with c.conn.begin():
            if not c.query_one("SELECT 1 FROM cc_ObjDes WHERE bk_obj_id=:o", {"o": oid}):
                raise CliError(EXIT_DEP, f"模型不存在: {oid}", "check_model")
            dbmod.ensure_object_unique_table(c)
            itbl, atbl = dbmod.instance_table(oid), dbmod.assoc_table(oid)
            if args.skip_if_exists and dbmod.table_exists(c, itbl):
                emit_result({'action': 'skip', 'human': f"实例表已存在，跳过: {itbl}"}, args.json)
                return EXIT_OK
            c.exec(INSTANCE_TABLE_DDL.format(tbl=quote_ident_raw(itbl)))
            c.exec(ASSOC_TABLE_DDL.format(tbl=quote_ident_raw(atbl)))
    emit_result({'action': 'create', 'human': f"已补建分表: {itbl} / {atbl}"}, args.json)
    return EXIT_OK


def cmd_model_show(args):
    oid = args.bk_obj_id
    validate_identifier(oid)
    with dbmod.cli_conn() as c:
        model = c.query_one("SELECT * FROM cc_ObjDes WHERE bk_obj_id=:o", {"o": oid})
        if not model:
            raise CliError(EXIT_DEP, f"模型不存在: {oid}", "check_model")
        groups = c.query_all("SELECT bk_group_id, bk_group_name, bk_isdefault FROM "
                             "cc_PropertyGroup WHERE bk_obj_id=:o ORDER BY bk_group_index",
                             {"o": oid})
        attrs = c.query_all("SELECT bk_property_id, bk_property_name, bk_property_type, "
                            "bk_property_group, isrequired, editable FROM cc_ObjAttDes "
                            "WHERE bk_obj_id=:o ORDER BY bk_property_index", {"o": oid})
    if args.json:
        print(json.dumps({"model": model, "groups": groups, "attributes": attrs},
                         ensure_ascii=False, default=str))
    else:
        print(f"模型: {oid} ({model.get('bk_obj_name')})")
        print(f"分组: {[ (g['bk_group_id']) for g in groups]}")
        print(f"属性({len(attrs)}):")
        for a in attrs:
            print(f"  - {a['bk_property_id']:20s} {a['bk_property_name']:12s} "
                  f"{a['bk_property_type']}")
    return EXIT_OK


def cmd_model_list(args):
    with dbmod.cli_conn() as c:
        models = c.query_all("SELECT bk_obj_id, bk_obj_name, bk_classification_id, "
                             "bk_ispaused FROM cc_ObjDes ORDER BY bk_obj_id")
    if args.json:
        print(json.dumps(models, ensure_ascii=False, default=str))
    else:
        for m in models:
            flag = " [停用]" if m.get('bk_ispaused') else ""
            print(f"  {m['bk_obj_id']:24s} {m['bk_obj_name']:16s} "
                  f"{m['bk_classification_id']}{flag}")
    return EXIT_OK


def cmd_model_delete(args):
    oid = args.bk_obj_id
    validate_identifier(oid)
    if not args.yes:
        raise CliError(EXIT_PARAM, "删除模型为危险操作，请加 --yes 确认", "confirm")
    with dbmod.cli_conn() as c:
        if args.dry_run:
            itbl, atbl = dbmod.instance_table(oid), dbmod.assoc_table(oid)
            print(f"[dry-run] DROP {itbl}; DROP {atbl}; DELETE 元数据 {oid}")
            return EXIT_OK
        with c.conn.begin():
            if not c.query_one("SELECT 1 FROM cc_ObjDes WHERE bk_obj_id=:o", {"o": oid}):
                raise CliError(EXIT_DEP, f"模型不存在: {oid}", "check_model")
            itbl, atbl = dbmod.instance_table(oid), dbmod.assoc_table(oid)
            if dbmod.table_exists(c, itbl):
                c.exec(f"DROP TABLE {quote_ident_raw(itbl)}")
            if dbmod.table_exists(c, atbl):
                c.exec(f"DROP TABLE {quote_ident_raw(atbl)}")
            c.exec("DELETE FROM cc_ObjAttDes WHERE bk_obj_id=:o", {"o": oid})
            c.exec("DELETE FROM cc_PropertyGroup WHERE bk_obj_id=:o", {"o": oid})
            c.exec("DELETE FROM cc_ObjectUnique WHERE bk_obj_id=:o", {"o": oid})
            c.exec("DELETE FROM cc_ObjDes WHERE bk_obj_id=:o", {"o": oid})
    emit_result({'action': 'delete', 'human': f"已删除模型: {oid}"}, args.json)
    return EXIT_OK


def _run_import(conn, kind, csv_path, opts, dry_run, skip_empty, json_out):
    if kind == 'classification':
        return do_classification_import(conn, csv_path, opts, dry_run, skip_empty)
    if kind == 'model':
        return do_model_import(conn, csv_path, opts, dry_run, skip_empty)
    if kind == 'attribute':
        return do_attribute_import(conn, csv_path, opts, dry_run, skip_empty)
    if kind == 'instance':
        return do_instance_import(conn, csv_path, opts, dry_run, skip_empty)
    raise CliError(EXIT_PARAM, f"未知导入类型: {kind}", "import")


def cmd_classification_import(args):
    opts = {'on_dup': args.on_duplicate, 'encoding': args.encoding,
            'delimiter': args.delimiter, 'strict': args.strict}
    # 核心内部已按行/按模型自行开事务，这里不再嵌套外层 begin
    with dbmod.cli_conn() as c:
        if args.dry_run:
            r = do_classification_import(c, args.csv, opts, True)
        else:
            r = do_classification_import(c, args.csv, opts, False)
    if r.get('failed'):
        emit_result(r, args.json)
        return EXIT_GENERAL
    emit_result(r, args.json)
    return EXIT_OK


def cmd_model_import(args):
    opts = {'on_dup': args.on_duplicate, 'encoding': args.encoding,
            'delimiter': args.delimiter, 'strict': args.strict,
            'with_system_props': args.with_system_props,
            'with_tables': args.with_tables, 'unique_by': 'bk_inst_name'}
    # 核心内部已按模型自行开事务，这里不再嵌套外层 begin
    with dbmod.cli_conn() as c:
        if args.dry_run:
            r = do_model_import(c, args.csv, opts, True)
        else:
            r = do_model_import(c, args.csv, opts, False)
    if r.get('failed'):
        emit_result(r, args.json)
        return EXIT_GENERAL
    emit_result(r, args.json)
    return EXIT_OK


def cmd_attribute_import(args):
    opts = {'bk_obj_id': args.bk_obj_id, 'on_dup': args.on_duplicate,
            'encoding': args.encoding, 'delimiter': args.delimiter,
            'strict': args.strict, 'group_auto_create': args.group_auto_create,
            'verbose': args.verbose}
    # 核心内部已按属性自行开事务，这里不再嵌套外层 begin
    with dbmod.cli_conn() as c:
        if args.dry_run:
            r = do_attribute_import(c, args.csv, opts, True)
        else:
            r = do_attribute_import(c, args.csv, opts, False)
    if r.get('failed'):
        emit_result(r, args.json)
        return EXIT_GENERAL
    emit_result(r, args.json)
    return EXIT_OK


def cmd_instance_import(args):
    opts = {'bk_obj_id': args.bk_obj_id, 'encoding': args.encoding,
            'delimiter': args.delimiter, 'mode': args.mode, 'upsert_key': args.upsert_key,
            'atomic': args.atomic, 'batch_size': args.batch_size,
            'generate_inst_id': args.generate_inst_id, 'enum_by_name': args.enum_by_name,
            'multivalue_sep': args.multivalue_sep,
            'skip_unknown_columns': args.skip_unknown_columns, 'strict': args.strict,
            'verbose': args.verbose, 'reject_out': args.reject_out}
    with dbmod.cli_conn() as c:
        if args.dry_run:
            r = do_instance_import(c, args.csv, opts, True)
        else:
            # do_instance_import 依赖调用方事务；始终开启以保证写入提交
            # （SQLite 下单事务即可，--no-atomic 与 --atomic 行为一致但均正确落库）
            with c.conn.begin():
                r = do_instance_import(c, args.csv, opts, False)
    emit_result(r, args.json)
    if not r.get('reconciled', True):
        return EXIT_GENERAL
    return EXIT_OK


# ---------------------------------------------------------------------------
# scaffold
# ---------------------------------------------------------------------------
def _seed_content():
    classifications = (['bk_classification_id', 'bk_classification_name', 'bk_classification_icon', 'ispre'],
                      [['bk_network', '网络设备', 'icon-cc-network', 'false'],
                       ['bk_application', '应用系统', 'icon-cc-application', 'false']])
    models = (['bk_obj_id', 'bk_obj_name', 'bk_classification_id', 'bk_obj_icon', 'ispre',
               'bk_ishidden', 'bk_ispaused', 'obj_sort_number'],
              [['bk_switch', '交换机', 'bk_network', 'icon-cc-switch', 'false', 'false', 'false', '0'],
               ['bk_deployment', '部署', 'bk_application', 'icon-cc-deployment', 'false', 'false', 'false', '1']])
    attr_header = ['英文名', '中文名', '数据类型', '字段分组', '数据配置', '单位', '描述', '提示',
                   '是否可编辑', '是否必填', '是否只读', '是否唯一', '字段索引']
    attr_types = ['文本', '文本', '文本', '文本', '文本', '文本', '文本', '文本',
                  '布尔', '布尔', '布尔', '布尔', '整型']
    attr_en = ['bk_property_id', 'bk_property_name', 'bk_property_type', 'bk_property_group',
               'option', 'unit', 'description', 'placeholder', 'editable', 'isrequired',
               'isreadonly', 'isonly', 'bk_property_index']
    attrs_switch = (attr_header,
                    attr_types,
                    attr_en,
                    [['bk_inst_name', '实例名', 'singlechar', 'default', '', '', '', '', 'true', 'true', 'false', 'true', '0'],
                     ['name', '名称', 'singlechar', 'default', '', '', '请输入名称', '', 'true', 'false', 'false', 'false', '10'],
                     ['status', '状态', 'enum', 'default',
                      '[{"id":"running","name":"运行中","type":"text","is_default":true},'
                      '{"id":"stopped","name":"已停止","type":"text","is_default":false}]',
                      '', '状态', '', 'false', 'false', 'false', 'false', '11'],
                     ['power_type', '电源类型', 'enummulti', 'default',
                      '[{"id":"AC","name":"AC","type":"text","is_default":false},'
                      '{"id":"DC","name":"DC","type":"text","is_default":false}]',
                      '', '电源', '', 'false', 'false', 'false', 'false', '12'],
                     ['management_ip', '管理IP', 'list', 'default',
                      '["192.168.1.1","192.168.1.2"]', '', '管理地址', '', 'false', 'false', 'false', 'false', '13'],
                     ['port_count', '端口数', 'int', 'default', '', '', '端口数量', '', 'false', 'false', 'false', 'false', '14'],
                     ['bk_backup', '是否备份', 'bool', 'default', '', '', '是否开启备份', '', 'false', 'false', 'false', 'false', '15'],
                     ['description', '描述', 'longchar', 'default', '', '', '设备描述', '', 'false', 'false', 'false', 'false', '16']])
    attrs_deployment = (attr_header,
                        attr_types,
                        attr_en,
                        [['bk_inst_name', '实例名', 'singlechar', 'default', '', '', '', '', 'true', 'true', 'false', 'true', '0'],
                     ['dep_hosts', '部署主机', 'singlechar', 'default', '', '', '部署目标主机', '', 'true', 'false', 'false', 'false', '10'],
                         ['dep_ns', '命名空间', 'singlechar', 'default', '', '', 'K8s 命名空间', '', 'true', 'false', 'false', 'false', '11'],
                         ['type', '部署类型', 'enum', 'default',
                          '[{"id":"blue","name":"蓝绿","type":"text","is_default":true},'
                          '{"id":"canary","name":"金丝雀","type":"text","is_default":false}]',
                          '', '部署策略', '', 'false', 'false', 'false', 'false', '12']])
    instances_switch = (['bk_inst_name', 'status', 'power_type', 'management_ip', 'port_count',
                         'bk_backup', 'description'],
                        [['核心交换机A', 'running', '["AC"]', '["192.168.1.1","192.168.1.2"]', '48', '1', '机房核心交换机'],
                         ['接入交换机B', 'stopped', '["AC","DC"]', '["192.168.1.3"]', '24', '0', '楼层接入']])
    return {
        'classifications.csv': classifications,
        'models.csv': models,
        'attributes_bk_switch.csv': attrs_switch,
        'attributes_bk_deployment.csv': attrs_deployment,
        'instances_bk_switch.csv': instances_switch,
    }


def cmd_scaffold_seed(args):
    ts = time.strftime('%y%m%d%H%M%S')
    out_dir = os.path.join(args.out_dir, ts)
    content = _seed_content()
    for fname, (header, *rest) in content.items():
        # classifications/models: rest == [data_rows]；attributes: rest == [attr_types, attr_en, data_rows]
        if len(rest) == 1:
            rows = rest[0]
        else:
            # 展开最后一项（data_rows 是属性行列表），使其每条属性成为独立 CSV 行
            *preamble, data_rows = rest
            rows = [*preamble, *data_rows]
        write_seed_csv(os.path.join(out_dir, fname), header, rows)
    emit_result({'action': 'seed', 'dir': out_dir,
                 'human': f"已生成 seed 目录: {out_dir}"}, args.json)
    return EXIT_OK


def cmd_scaffold_spec(args):
    with open(args.file, 'r', encoding='utf-8') as f:
        spec = parse_json(f.read())
    if not spec:
        raise CliError(EXIT_PARAM, f"规格解析失败: {args.file}", "spec")
    # 预检（§5.6 spec 预检）：必填字段缺失即退出码 2，避免运行时 TypeError/KeyError 落到 1
    cls = spec.get('classification')
    model = spec.get('model')
    if not isinstance(model, dict) or not model.get('bk_obj_id'):
        raise CliError(EXIT_PARAM, "spec 缺少必填字段 model.bk_obj_id", "spec")
    if cls is not None and (not isinstance(cls, dict) or not cls.get('bk_classification_id')):
        raise CliError(EXIT_PARAM, "spec.classification 缺少 bk_classification_id", "spec")
    groups = spec.get('groups') or []
    attributes = spec.get('attributes') or []
    o = {
        'bk_obj_id': model['bk_obj_id'],
        'bk_obj_name': model['bk_obj_name'],
        'bk_classification_id': model['bk_classification_id'],
        'bk_obj_icon': model.get('bk_obj_icon', 'icon-cc-default'),
        'ispre': model.get('ispre', False),
        'bk_ishidden': False, 'bk_ispaused': False,
        'obj_sort_number': model.get('obj_sort_number', 0),
        'with_system_props': True, 'with_tables': True,
        'unique_by': 'bk_inst_name', 'on_dup': args.on_duplicate,
    }
    with dbmod.cli_conn() as c:
        if args.dry_run:
            print("[dry-run] scaffold spec -> classification + model + attributes")
            return EXIT_OK
        with c.conn.begin():
            if cls:
                create_classification_core(c, cls['bk_classification_id'],
                                           cls['bk_classification_name'],
                                           cls.get('bk_classification_icon', 'icon-cc-default'),
                                           cls.get('ispre', False), 'skip', False)
            create_model_core(c, o, False)
            for g in groups:
                if not c.query_one("SELECT 1 FROM cc_PropertyGroup WHERE bk_obj_id=:o AND bk_group_id=:g",
                                    {"o": o['bk_obj_id'], "g": g['bk_group_id']}):
                    c.exec(
                        "INSERT INTO cc_PropertyGroup "
                        "(_id, id, bk_obj_id, bk_group_id, bk_group_name, bk_group_index, "
                        "bk_isdefault, is_collapse, ispre, bk_biz_id, creator, modifier, "
                        "bk_supplier_account) VALUES "
                        "(:_id, :id, :bk_obj_id, :bk_group_id, :bk_group_name, :bk_group_index, "
                        ":bk_isdefault, false, true, 0, 'admin', 'admin', '0')",
                        {"_id": f"{o['bk_obj_id']}.{g['bk_group_id']}", "id": generate_id(),
                         "bk_obj_id": o['bk_obj_id'], "bk_group_id": g['bk_group_id'],
                         "bk_group_name": g['bk_group_name'],
                         "bk_group_index": g.get('bk_group_index', 0),
                         "bk_isdefault": g.get('bk_isdefault', False)})
            for a in attributes:
                p = {
                    'bk_property_id': a['bk_property_id'],
                    'bk_property_name': a['bk_property_name'],
                    'bk_property_type': a['bk_property_type'],
                    'bk_property_group': a.get('bk_property_group', 'default'),
                    'isrequired': a.get('isrequired', False),
                    'editable': a.get('editable', True),
                    'bk_ishidden': a.get('bk_ishidden', False),
                    'bk_isapi': a.get('bk_isapi', False),
                    'bk_issystem': a.get('bk_issystem', False),
                    'ispre': a.get('ispre', False),
                    'isreadonly': a.get('isreadonly', False),
                    'isonly': a.get('isonly', False),
                    'ismultiple': a.get('ismultiple', False),
                    'bk_property_index': a.get('bk_property_index', 0),
                    'option': _normalize_option(a['bk_property_type'], a.get('option')) if a.get('option') else None,
                    'placeholder': a.get('placeholder', ''),
                    'unit': a.get('unit', ''),
                }
                add_attribute_core(c, o['bk_obj_id'], p, False, on_dup='overwrite')
    emit_result({'action': 'spec', 'bk_obj_id': o['bk_obj_id'],
                 'human': f"scaffold spec 完成: {o['bk_obj_id']}"}, args.json)
    return EXIT_OK


def cmd_scaffold_apply(args):
    d = args.dir
    if not os.path.isdir(d):
        raise CliError(EXIT_PARAM, f"目录不存在: {d}", "dir")
    files = sorted(f for f in os.listdir(d) if f.endswith('.csv'))
    plan = []  # (order, kind, path, opts)
    for f in files:
        if f == 'classifications.csv':
            plan.append(('1', 'classification', os.path.join(d, f),
                         {'on_dup': args.on_duplicate, 'encoding': 'utf-8-sig',
                          'delimiter': ',', 'strict': args.strict}))
        elif f == 'models.csv':
            plan.append(('2', 'model', os.path.join(d, f),
                         {'on_dup': args.on_duplicate, 'encoding': 'utf-8-sig',
                          'delimiter': ',', 'strict': args.strict,
                          'with_system_props': args.with_system_props,
                          'with_tables': args.with_tables, 'unique_by': 'bk_inst_name'}))
        elif f.startswith('attributes_') and f.endswith('.csv'):
            oid = f[len('attributes_'):-4]
            plan.append(('3', 'attribute', os.path.join(d, f),
                         {'bk_obj_id': oid, 'on_dup': args.on_duplicate,
                          'encoding': 'utf-8-sig', 'delimiter': ',',
                          'strict': args.strict, 'group_auto_create': args.group_auto_create,
                          'verbose': args.verbose}))
        elif f.startswith('instances_') and f.endswith('.csv'):
            oid = f[len('instances_'):-4]
            plan.append(('4', 'instance', os.path.join(d, f),
                         {'bk_obj_id': oid, 'encoding': 'utf-8-sig', 'delimiter': ',',
                          'mode': 'auto', 'atomic': args.atomic, 'batch_size': 500,
                          'generate_inst_id': True, 'enum_by_name': False,
                          'multivalue_sep': ',', 'skip_unknown_columns': False,
                          'strict': args.strict, 'verbose': args.verbose,
                          'reject_out': None, 'batch_id': f"seed/{os.path.basename(d)}"}))

    if not plan:
        raise CliError(EXIT_PARAM, "目录内未发现可执行的 CSV", "empty_dir")

    stages = []
    batch_id = f"seed/{os.path.basename(d.rstrip('/'))}"
    if args.dry_run:
        for order, kind, path, opts in plan:
            print(f"[dry-run] stage {order}: {kind} <- {os.path.basename(path)}")
        return EXIT_OK

    # 严格按阶段序执行（分类→模型→属性→实例），否则属性/实例会在模型创建前触发
    # "模型不存在"。import 核心（classification/model/attribute）各自内部已开事务，
    # 此处禁止再套外层 begin；仅 instance 核心依赖调用方事务，统一包裹。
    plan.sort(key=lambda t: t[0])

    with dbmod.cli_conn() as c:
        for order, kind, path, opts in plan:
            opts['batch_id'] = batch_id
            if kind == 'instance':
                with c.conn.begin():
                    r = _run_import(c, kind, path, opts, False, skip_empty=True,
                                    json_out=args.json)
            else:
                r = _run_import(c, kind, path, opts, False, skip_empty=True,
                                json_out=args.json)
            stages.append({'stage': kind, **r})

    # 运行清单（M3）
    manifest_out = args.manifest_out or os.path.join(d, '.run.json')
    write_manifest(manifest_out, {
        'command': 'scaffold apply', 'dir': os.path.abspath(d), 'batch_id': batch_id,
        'ts': now_iso(), 'stages': stages,
    })
    reconciled_all = all(s.get('reconciled', True) for s in stages)
    if args.json:
        print(json.dumps({'stages': stages, 'reconciled': reconciled_all},
                         ensure_ascii=False, default=str))
    else:
        for s in stages:
            print(f"  [{s['stage']}] {s.get('human','')}")
        print(f"运行清单: {manifest_out}  对账: {'✓' if reconciled_all else '✗'}")
    return EXIT_OK if reconciled_all else EXIT_GENERAL


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------
def build_parser():
    # 公共父解析器：全局选项在子命令前/后均可（设计文档 §4）
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--db', help='SQLite 文件路径（默认走 settings 的 cmdb_dev.db）')
    common.add_argument('--env', default='development',
                        help='环境（default/development/testing/production）')
    common.add_argument('--dry-run', action='store_true', help='仅打印将执行的 SQL，不落库')
    common.add_argument('--json', action='store_true', help='JSON 输出')
    common.add_argument('--yes', '-y', action='store_true', help='跳过危险操作二次确认')

    p = argparse.ArgumentParser(prog='cmdb', parents=[common], description='CMDB-Lite 命令行工具')
    sub = p.add_subparsers(dest='cmd', required=True,
                           parser_class=lambda **a: argparse.ArgumentParser(parents=[common], **a))

    def add_dup(sp, default):
        sp.add_argument('--on-duplicate', default=default,
                        choices=['error', 'skip', 'overwrite'])

    # classification create
    sp = sub.add_parser('classification', help='模型分类')
    css = sp.add_subparsers(dest='sub', required=True,
                     parser_class=lambda **a: argparse.ArgumentParser(parents=[common], **a))
    x = css.add_parser('create')
    x.add_argument('--bk_classification_id', required=True)
    x.add_argument('--bk_classification_name', required=True)
    x.add_argument('--bk_classification_icon', default='icon-cc-default')
    x.add_argument('--ispre', type=parse_bool, default=False)
    add_dup(x, 'error')
    x.set_defaults(func=cmd_classification_create)
    x = css.add_parser('import')
    x.add_argument('--csv', required=True)
    x.add_argument('--encoding', default='utf-8-sig')
    x.add_argument('--delimiter', default=',')
    x.add_argument('--atomic', dest='atomic', action='store_true', default=True)
    x.add_argument('--no-atomic', dest='atomic', action='store_false')
    x.add_argument('--strict', action='store_true')
    add_dup(x, 'overwrite')
    x.set_defaults(func=cmd_classification_import)

    # model
    sp = sub.add_parser('model', help='模型')
    ms = sp.add_subparsers(dest='sub', required=True,
                     parser_class=lambda **a: argparse.ArgumentParser(parents=[common], **a))
    x = ms.add_parser('create')
    x.add_argument('--bk_obj_id', required=True)
    x.add_argument('--bk_obj_name', required=True)
    x.add_argument('--bk_classification_id', required=True)
    x.add_argument('--bk_obj_icon', default='icon-cc-default')
    x.add_argument('--ispre', type=parse_bool, default=False)
    x.add_argument('--obj_sort_number', type=int, default=0)
    x.add_argument('--with-system-props', dest='with_system_props', action='store_true', default=True)
    x.add_argument('--no-with-system-props', dest='with_system_props', action='store_false')
    x.add_argument('--with-tables', dest='with_tables', action='store_true', default=True)
    x.add_argument('--no-with-tables', dest='with_tables', action='store_false')
    x.add_argument('--unique-by', default='bk_inst_name')
    add_dup(x, 'error')
    x.set_defaults(func=cmd_model_create)
    x = ms.add_parser('import')
    x.add_argument('--csv', required=True)
    x.add_argument('--encoding', default='utf-8-sig')
    x.add_argument('--delimiter', default=',')
    x.add_argument('--with-system-props', dest='with_system_props', action='store_true', default=True)
    x.add_argument('--no-with-system-props', dest='with_system_props', action='store_false')
    x.add_argument('--with-tables', dest='with_tables', action='store_true', default=True)
    x.add_argument('--no-with-tables', dest='with_tables', action='store_false')
    x.add_argument('--atomic', dest='atomic', action='store_true', default=True)
    x.add_argument('--no-atomic', dest='atomic', action='store_false')
    x.add_argument('--strict', action='store_true')
    add_dup(x, 'overwrite')
    x.set_defaults(func=cmd_model_import)
    x = ms.add_parser('show')
    x.add_argument('--bk_obj_id', required=True)
    x.set_defaults(func=cmd_model_show)
    x = ms.add_parser('list')
    x.set_defaults(func=cmd_model_list)
    x = ms.add_parser('delete')
    x.add_argument('--bk_obj_id', required=True)
    x.set_defaults(func=cmd_model_delete)

    # attribute
    sp = sub.add_parser('attribute', help='属性')
    asp = sp.add_subparsers(dest='sub', required=True,
                     parser_class=lambda **a: argparse.ArgumentParser(parents=[common], **a))
    x = asp.add_parser('create')
    x.add_argument('--bk_obj_id', required=True)
    x.add_argument('--bk_property_id', required=True)
    x.add_argument('--bk_property_name', required=True)
    x.add_argument('--bk_property_type', required=True)
    x.add_argument('--bk_property_group', default='default')
    x.add_argument('--isrequired', type=parse_bool, default=False)
    x.add_argument('--editable', type=parse_bool, default=True)
    x.add_argument('--bk_ishidden', type=parse_bool, default=False)
    x.add_argument('--bk_isapi', type=parse_bool, default=False)
    x.add_argument('--bk_issystem', type=parse_bool, default=False)
    x.add_argument('--ispre', type=parse_bool, default=False)
    x.add_argument('--ismultiple', type=parse_bool, default=False)
    x.add_argument('--bk_property_index', type=int, default=0)
    x.add_argument('--option', default=None)
    x.add_argument('--placeholder', default=None)
    x.add_argument('--unit', default=None)
    add_dup(x, 'error')
    x.set_defaults(func=cmd_attribute_create)
    x = asp.add_parser('import')
    x.add_argument('--csv', required=True)
    x.add_argument('--bk_obj_id', required=True)
    x.add_argument('--encoding', default='utf-8-sig')
    x.add_argument('--delimiter', default=',')
    x.add_argument('--group-auto-create', action='store_true')
    x.add_argument('--atomic', dest='atomic', action='store_true', default=True)
    x.add_argument('--no-atomic', dest='atomic', action='store_false')
    x.add_argument('--strict', action='store_true')
    x.add_argument('--verbose', action='store_true')
    add_dup(x, 'overwrite')
    x.set_defaults(func=cmd_attribute_import)

    # instance
    sp = sub.add_parser('instance', help='实例')
    isp = sp.add_subparsers(dest='sub', required=True,
                     parser_class=lambda **a: argparse.ArgumentParser(parents=[common], **a))
    x = isp.add_parser('import')
    x.add_argument('--csv', required=True)
    x.add_argument('--bk_obj_id', required=True)
    x.add_argument('--encoding', default='utf-8-sig')
    x.add_argument('--delimiter', default=',')
    x.add_argument('--mode', default='auto', choices=['auto', 'insert', 'upsert'])
    x.add_argument('--upsert-key', default=None)
    x.add_argument('--atomic', dest='atomic', action='store_true', default=True)
    x.add_argument('--no-atomic', dest='atomic', action='store_false')
    x.add_argument('--generate-inst-id', dest='generate_inst_id', action='store_true', default=True)
    x.add_argument('--no-generate-inst-id', dest='generate_inst_id', action='store_false')
    x.add_argument('--enum-by-name', action='store_true')
    x.add_argument('--multivalue-sep', default=',')
    x.add_argument('--skip-unknown-columns', action='store_true')
    x.add_argument('--batch-size', type=int, default=500)
    x.add_argument('--strict', action='store_true')
    x.add_argument('--verbose', action='store_true')
    x.add_argument('--reject-out', default=None)
    x.set_defaults(func=cmd_instance_import)

    # table
    sp = sub.add_parser('table', help='实例表')
    ts = sp.add_subparsers(dest='sub', required=True,
                     parser_class=lambda **a: argparse.ArgumentParser(parents=[common], **a))
    x = ts.add_parser('create')
    x.add_argument('--bk_obj_id', required=True)
    x.add_argument('--skip-if-exists', dest='skip_if_exists', action='store_true', default=True)
    x.add_argument('--no-skip-if-exists', dest='skip_if_exists', action='store_false')
    x.set_defaults(func=cmd_table_create)

    # scaffold
    sp = sub.add_parser('scaffold', help='规格驱动（spec / seed / apply）')
    scs = sp.add_subparsers(dest='sub', required=True,
                     parser_class=lambda **a: argparse.ArgumentParser(parents=[common], **a))
    x = scs.add_parser('spec')
    x.add_argument('--file', required=True)
    x.add_argument('--on-duplicate', default='skip')
    x.set_defaults(func=cmd_scaffold_spec)
    x = scs.add_parser('seed')
    x.add_argument('--out-dir', default='./seed')
    x.set_defaults(func=cmd_scaffold_seed)
    x = scs.add_parser('apply')
    x.add_argument('--dir', required=True)
    x.add_argument('--on-duplicate', default='overwrite')
    x.add_argument('--with-system-props', dest='with_system_props', action='store_true', default=True)
    x.add_argument('--with-tables', dest='with_tables', action='store_true', default=True)
    x.add_argument('--atomic', dest='atomic', action='store_true', default=True)
    x.add_argument('--no-atomic', dest='atomic', action='store_false')
    x.add_argument('--group-auto-create', action='store_true')
    x.add_argument('--strict', action='store_true')
    x.add_argument('--verbose', action='store_true')
    x.add_argument('--manifest-out', default=None)
    x.set_defaults(func=cmd_scaffold_apply)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        dbmod.init_cli_db(args.db, args.env)
        return args.func(args)
    except CliError as e:
        emit_error(e.code, e.msg, e.step, args.json)
        return e.code
    except InvalidIdentifierError as e:
        emit_error(EXIT_PARAM, str(e), "identifier", args.json)
        return EXIT_PARAM
    except FileNotFoundError as e:
        emit_error(EXIT_PARAM, f"文件不存在: {e}", "file", args.json)
        return EXIT_PARAM
    except OperationalError as e:
        msg = str(e)
        if 'locked' in msg.lower():
            emit_error(EXIT_DB, f"数据库被锁定（database is locked），请先停止后端占用连接: {msg}",
                       "db", args.json)
            return EXIT_DB
        emit_error(EXIT_GENERAL, f"SQL 执行失败: {msg}", "db", args.json)
        return EXIT_GENERAL
    except Exception as e:  # noqa: BLE001
        emit_error(EXIT_GENERAL, f"未预期错误: {e}", None, args.json)
        return EXIT_GENERAL


if __name__ == '__main__':
    sys.exit(main())
