
#!/usr/bin/env python3
"""
数据库初始化迁移工具（执行层）

模块职责边界（整改后）：

===============  ===================================================
本模块            迁移【流程】：建表、按序执行各迁移步骤、存量库升级与
                  数据归一，全部数据库访问经 app/db/executor（连接池 +
                  方言适配的单一入口）。
app/migrate/seeds.py   迁移【数据】：预置分类/模型/属性/分组/关联类型/
                  主机挂载等种子清单（无数据库访问逻辑）。
app/sql/migrate/*.sql  迁移【SQL】：参数化的固定语句，以 PostgreSQL 规范
                  方言书写，运行时由执行层转译为当前目标方言。
app/db/dialect.py      方言【差异】：upsert() 生成三库各自的幂等写法、
                  get_sql_type()/内省函数等。
===============  ===================================================

因此本模块不直接 import sqlglot / sqlalchemy，也不再内联种子数据。

枚举选项格式（原项目标准格式）：
- enum（单选枚举）: [{"id": "xxx", "name": "显示名", "type": "text", "is_default": false}]
- enummulti（多选枚举）: [{"id": "xxx", "name": "显示名", "type": "text", "is_default": false}]
- list（列表）: ["选项1", "选项2"]
- int: {"min": 0, "max": 100}
- float: {"min": 0.0, "max": 100.5}
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
import coloredlogs
import logging

# 数据库访问统一走执行器层（连接池 + 方言适配的单一入口）。
# 迁移工具不直接依赖 sqlglot / sqlalchemy.text / get_connection —— 方言转译与
# 连接管理是 app/db/{dialect,engine,executor} 的职责，此处只表达"迁移要做什么"。
from app.db.executor import execute as db_execute, query_all as db_query_all
from app.db.dialect import get_column_names, list_table_names, current_dialect, index_exists, upsert
from app.config.settings import get_config
from app.utils.tools import generate_id
from app.definitions import (
    get_sql_type,
    VALID_PROPERTY_TYPES,
    ASSOCIATION_PROPERTY_TYPES,
    LEGACY_PROPERTY_TYPE_ALIAS,
    KNOWN_GROUP_NAMES,
    model_name_property,
    VALID_ASST_DIRECTIONS,
    normalize_asst_direction,
)
# 种子数据来自 app/migrate/seeds.py（单一来源）。
# 这里显式列名导入而非 `import *`：既让本模块的依赖面一目了然，也使
# `app.migrate.migrate.SYSTEM_PROPERTIES` 等既有引用路径继续可用
# （app/cli/cmdb.py、scripts/seed_hosts.py、docs/ 均按该路径引用），
# 搬迁对外部调用方零破坏。新增代码请直接从 app.migrate.seeds 导入。
from app.migrate.seeds import (  # noqa: F401  (部分名称仅为向后兼容而 re-export)
    convert_enum_option,
    parse_enum_option,
    HOST_BINDING_SPEC,
    SYSTEM_FIELDS,
    DEFAULT_OBJ_ICON,
    DEFAULT_CLASSIFICATION_ICON,
    DEFAULT_ASST_ICON,
    SYSTEM_PROPERTIES,
    BUILTIN_TIME_PROPERTY_INDEX,
    BUILTIN_TIME_PROPERTIES,
    BUILTIN_MODELS,
    BUILTIN_MODEL_ATTRIBUTES,
    MODEL_CLASSIFICATION_MAP,
    CLASSIFICATIONS,
    PROPERTY_GROUPS,
    BUILTIN_DEFAULT_GROUP_NAME,
    GENERIC_DEFAULT_GROUP_NAME,
    DEFAULT_GROUP_BUILTIN_MODELS,
    EXTRA_GROUP_DEFS,
    GROUP_ID_MIGRATION,
    PROPERTY_GROUP_UPDATE_MAP,
    ASSOCIATION_KIND_SEEDS,
    OBJECT_ASSOCIATION_SEEDS,
)


# 配置日志
logger = logging.getLogger('migrate')
coloredlogs.install(level='INFO', logger=logger)


class DatabaseMigrator:
    # ── 多处复用的写入列清单（避免同一张表的列在多个方法里各写一份而漂移）──
    # cc_ObjDes：migrate_models（外部模型定义）与 migrate_builtin_models（内置模型）
    # 写入完全相同的列，仅 bk_isresourcedir 取值来源不同。
    OBJDES_COLUMNS = [
        '_id', 'id', 'bk_obj_id', 'bk_obj_name', 'bk_obj_icon', 'bk_classification_id',
        'ispre', 'bk_supplier_account', 'creator', 'modifier', 'obj_sort_number',
        'bk_isresourcedir',
    ]
    OBJDES_LITERALS = {'bk_supplier_account': "'0'", 'creator': "'admin'", 'modifier': "'admin'"}

    # cc_ObjAttDes：属性定义表，被 5 个迁移步骤写入（内置模型属性 / 内置时间属性 /
    # 外部属性 ×2 / 主线 parent 属性），此前 5 处各写一份 21~22 列的 INSERT。
    # 主键是复合键 (bk_obj_id, bk_property_id) —— upsert 冲突键必须同时给两列。
    OBJATTDES_COLUMNS = [
        '_id', 'id', 'bk_obj_id', 'bk_property_id', 'bk_property_name', 'bk_property_type',
        'bk_property_group', 'isrequired', 'bk_ispassword', 'bk_ishidden', 'isreadonly',
        'isonly', 'bk_isapi', 'bk_issystem', 'option', 'unit', 'placeholder', 'editable',
        'ispre', 'bk_property_index', 'bk_supplier_account',
    ]
    # 业务属性（JSON 资源）额外带 ismultiple（多选枚举标志），列集比内置属性多一列。
    OBJATTDES_COLUMNS_WITH_MULTI = [
        '_id', 'id', 'bk_obj_id', 'bk_property_id', 'bk_property_name', 'bk_property_type',
        'bk_property_group', 'isrequired', 'bk_ispassword', 'bk_ishidden', 'isreadonly',
        'isonly', 'bk_isapi', 'bk_issystem', 'ismultiple', 'option', 'unit', 'placeholder',
        'editable', 'ispre', 'bk_property_index', 'bk_supplier_account',
    ]
    OBJATTDES_LITERALS = {'bk_supplier_account': "'0'"}
    OBJATTDES_CONFLICT = ('bk_obj_id', 'bk_property_id')

    def __init__(self, config=None):
        self.config = config or get_config()
        self.project_root = Path(__file__).parent.parent.parent
        self.workspace_root = self.project_root.parent
        
    # ── 执行层：统一委托 app.db.executor（与运行期服务同一入口）──────────────
    # 此前这两个方法自建 get_connection() + text(adapt_sql()) + 行转字典，
    # 与 executor.SQLExecutor 的实现完全重复。重复实现的代价是：executor 后续
    # 增加的能力（慢查询埋点、重试、连接归还语义、SQL 文件路径解析）迁移工具
    # 一概享受不到，且两套代码对 adapt_sql 的调用时机若发生偏差就会出现
    # "服务能跑、迁移报方言错"这类难查问题。
    # 现统一委托：迁移与运行期共用同一执行入口、同一连接池、同一方言适配路径。
    # 方法签名保持不变，80 处既有调用点无需改动。
    def execute_sql(self, sql, params=None):
        """执行 SQL 语句（写/DDL）

        Args:
            sql: SQL 语句，或 ``<module>/<file>.sql`` 形式的 SQL 文件路径
                 （由 executor._resolve_sql 解析，见 app/sql/migrate/）
            params: 绑定参数字典

        经 executor → adapt_sql 转译为当前目标方言（SQLite/MySQL/PostgreSQL）。
        """
        db_execute(sql, params or {})

    def execute_query(self, sql, params=None):
        """执行查询并返回字典列表

        Args:
            sql: SELECT 语句，或 ``<module>/<file>.sql`` 形式的 SQL 文件路径
            params: 绑定参数字典
        """
        return db_query_all(sql, params or {})

    @staticmethod
    def upsert_sql(table, columns, conflict, literals=None):
        """生成三库通用的幂等写入语句（迁移期唯一的 upsert 入口）。

        Args:
            table: 表名（未引号化）
            columns: 全部写入列（未引号化）
            conflict: 冲突判定列 —— **必须是该表的主键或唯一键**，
                      否则 PostgreSQL 会报
                      "no unique or exclusion constraint matching the ON CONFLICT
                      specification"。取业务唯一键（如 bk_obj_id / bk_asst_id）
                      而非自增 id，才能表达"同一业务对象原位更新"。
            literals: ``{列名: SQL 字面量}``，用于 ``'admin'`` / ``'0'`` / ``1``
                      这类不走绑定参数的固定值；未列出的列一律用 ``:列名`` 占位符。

        Returns:
            当前方言下的完整 INSERT 语句：
              sqlite   → INSERT OR REPLACE
              mysql    → INSERT ... ON DUPLICATE KEY UPDATE
              postgres → INSERT ... ON CONFLICT(冲突列) DO UPDATE SET ...

        为什么不直接写 ``INSERT OR REPLACE``：那是 SQLite 专属语法。虽然
        ``adapt_sql`` 有正则兜底改写，但兜底把冲突键藏在 ``dialect._CONFLICT_MAP``
        的表名映射里（改表结构时容易漏改），且其正则以 ``[^)]*`` 匹配列/值，
        值中出现函数调用括号即截断。显式生成把冲突键留在调用现场，语义自证。

        注意：调用必须发生在**运行期方法内**而非 import 期 —— 语句内容依赖
        ``current_dialect()``，import 期引擎可能尚未按配置初始化。
        """
        literals = literals or {}
        placeholders = [literals.get(col, f':{col}') for col in columns]
        return upsert(table=table, columns=columns,
                      placeholders=placeholders, conflict=conflict)
    
    def migrate_classifications(self):
        """迁移分类数据

        经 dialect.upsert 生成三库通用的幂等 Upsert（冲突键 bk_classification_id）：
        - sqlite   → INSERT OR REPLACE
        - mysql    → INSERT ... ON DUPLICATE KEY UPDATE
        - postgres → INSERT ... ON CONFLICT(bk_classification_id) DO UPDATE
        重跑迁移时按分类 ID 原位合并，不会因主键 id 不同而插入重复分类；
        可修正早期「模型注册时自动建占位分类」产生的脏数据
        （bk_classification_name 被误写成分类 ID 字符串、icon 为默认图标）。
        """
        # 说明：此前此处硬编码 PG 的 ON CONFLICT 语法，而 adapt_sql 识别到
        # ON CONFLICT 标记后会跳过转译，导致该语句在 MySQL 下原样执行并报语法错误。
        # 现统一经 upsert_sql() 由目标方言生成对应写法，三库一致。
        # 语句在循环外生成一次（内容与行数据无关，逐行重复生成纯属浪费）。
        sql = self.upsert_sql(
            'cc_ObjClassification',
            ['id', 'bk_classification_id', 'bk_classification_name',
             'bk_classification_icon', 'ispre', 'classification_index',
             'bk_supplier_account'],
            conflict='bk_classification_id',
            literals={'bk_supplier_account': "'0'"},
        )
        for cls in CLASSIFICATIONS:
            self.execute_sql(sql, {
                "id": cls["id"],
                "bk_classification_id": cls["bk_classification_id"],
                "bk_classification_name": cls["bk_classification_name"],
                "bk_classification_icon": cls.get("bk_classification_icon") or DEFAULT_CLASSIFICATION_ICON,
                "ispre": cls["ispre"],
                "classification_index": cls.get("classification_index", cls["id"])
            })
        logger.info(f"迁移 {len(CLASSIFICATIONS)} 个分类")
    
    def migrate_property_groups(self):
        """迁移属性分组数据"""
        # 先获取所有模型
        models = self.execute_query('migrate/select_all_model_ids.sql')

        for model in models:
            model_id = model['bk_obj_id']
            for group in PROPERTY_GROUPS:
                # 默认分组显示名按模型类型区分（bk_group_id 始终是 "default"，与显示名无关）：
                #   内置模型(biz/set/module/host) -> 「基础信息」(BaseInfoName)
                #   通用/普通模型               -> 「Default」(logics/model/object.go:150 硬编码)
                # 注意：PROPERTY_GROUPS 的 bk_group_name 仅为内置默认名，通用模型须显式取
                # GENERIC_DEFAULT_GROUP_NAME，切勿回退到 group['bk_group_name']（仍是「基础信息」）。
                is_default_grp = bool(group.get('bk_isdefault')) or group.get('bk_group_id') == 'default'
                if is_default_grp:
                    bk_group_name = (BUILTIN_DEFAULT_GROUP_NAME
                                     if model_id in DEFAULT_GROUP_BUILTIN_MODELS
                                     else GENERIC_DEFAULT_GROUP_NAME)
                else:
                    bk_group_name = group['bk_group_name']
                # 去重写入：cc_PropertyGroup 主键为自增 id，_id 非唯一，
                # 旧版 INSERT OR REPLACE 仅按 id 判重，会在「模型已存在 default 行」
                # 时插入第二条同名分组（如旧的「默认」与新的「基础信息」并存）。
                # 这里改为先查后更：复用既有 id 把分组定义刷新为规范值，
                # 并删除该 (bk_obj_id, bk_group_id) 下的其他残留行，保证每组唯一。
                existing = self.execute_query(
                    "SELECT id FROM cc_PropertyGroup "
                    "WHERE bk_obj_id = :mid AND bk_group_id = :gid ORDER BY id",
                    {'mid': model_id, 'gid': group['bk_group_id']}
                )
                if existing:
                    canonical_id = existing[0]['id']
                    # 原位刷新分组定义（外置 SQL：migrate/update_property_group.sql）
                    self.execute_sql('migrate/update_property_group.sql', {
                        '_id': f"{model_id}.{group['bk_group_id']}",
                        'bk_group_name': bk_group_name,
                        'bk_group_index': group['bk_group_index'],
                        'bk_isdefault': group['bk_isdefault'],
                        'is_collapse': group['is_collapse'],
                        'ispre': group['ispre'],
                        'id': canonical_id,
                    })
                    if len(existing) > 1:
                        extra_ids = [r['id'] for r in existing[1:]]
                        placeholders = ", ".join(f":eid_{i}" for i in range(len(extra_ids)))
                        del_params = {f"eid_{i}": v for i, v in enumerate(extra_ids)}
                        self.execute_sql(
                            f"DELETE FROM cc_PropertyGroup WHERE id IN ({placeholders})",
                            del_params
                        )
                        logger.info(
                            f"清理重复分组 {group['bk_group_id']} "
                            f"（模型 {model_id}）：{len(extra_ids)} 行"
                        )
                else:
                    # 省略 id 列，由 SQLite 对 INTEGER PRIMARY KEY 自动取 MAX(id)+1，
                    # 避免复用既有 id 触发主键冲突。
                    # 缺失分组补全（外置 SQL：migrate/insert_property_group.sql）
                    self.execute_sql('migrate/insert_property_group.sql', {
                        '_id': f"{model_id}.{group['bk_group_id']}",
                        'bk_obj_id': model_id,
                        'bk_group_id': group['bk_group_id'],
                        'bk_group_name': bk_group_name,
                        'bk_group_index': group['bk_group_index'],
                        'bk_isdefault': group['bk_isdefault'],
                        'is_collapse': group['is_collapse'],
                        'ispre': group['ispre']
                    })

        # 空值规范化：对齐上游 bk-cmdb 的 checkAttributeGroupExist —
        # 当属性未指定分组时，落库值固定为 common.BKDefaultField（即小写 "default"），
        # 而不是留空串。留空会在 cc_PropertyGroup 上形成悬空引用，
        # 前端只能靠 `bk_property_group || 'default'` 兜底，数据层不干净。
        blank_rows = self.execute_query(
            "SELECT COUNT(*) AS n FROM cc_ObjAttDes "
            "WHERE bk_property_group IS NULL OR TRIM(bk_property_group) = ''"
        )
        blank_cnt = blank_rows[0]['n'] if blank_rows else 0
        if blank_cnt:
            self.execute_sql(
                "UPDATE cc_ObjAttDes SET bk_property_group = 'default' "
                "WHERE bk_property_group IS NULL OR TRIM(bk_property_group) = ''"
            )
            logger.info(f"规范化空 bk_property_group -> 'default'，共 {blank_cnt} 条")

        # 历史分组 ID 归并：把 lite 自造的 base / agent 收敛到上游标准 default / auto。
        # 先迁移属性引用，再清理 cc_PropertyGroup 中的旧分组行，避免出现悬空引用。
        for old_gid, new_gid in GROUP_ID_MIGRATION.items():
            moved = self.execute_query(
                "SELECT COUNT(*) AS n FROM cc_ObjAttDes WHERE bk_property_group = :g",
                {'g': old_gid}
            )
            moved_cnt = moved[0]['n'] if moved else 0
            if moved_cnt:
                self.execute_sql(
                    "UPDATE cc_ObjAttDes SET bk_property_group = :new "
                    "WHERE bk_property_group = :old",
                    {'new': new_gid, 'old': old_gid}
                )
                logger.info(f"归并分组 {old_gid} -> {new_gid}，迁移属性 {moved_cnt} 条")
            # 旧分组定义行一并删除，其属性已迁走
            stale = self.execute_query(
                "SELECT COUNT(*) AS n FROM cc_PropertyGroup WHERE bk_group_id = :g",
                {'g': old_gid}
            )
            if stale and stale[0]['n']:
                self.execute_sql(
                    "DELETE FROM cc_PropertyGroup WHERE bk_group_id = :g", {'g': old_gid}
                )
                logger.info(f"清理旧分组定义 {old_gid}，共 {stale[0]['n']} 行")

        existing_groups = {
            (row['bk_obj_id'], row['bk_group_id'])
            for row in self.execute_query(
                "SELECT bk_obj_id, bk_group_id FROM cc_PropertyGroup"
            )
        }
        # 该模型属性上实际出现的分组集合（去重，跳过空串）
        used_groups = {}
        for row in self.execute_query(
            "SELECT bk_obj_id, bk_property_group FROM cc_ObjAttDes"
        ):
            mid = row['bk_obj_id']
            gid = row['bk_property_group'] or 'default'
            if not gid or gid.strip() == '':
                gid = 'default'
            used_groups.setdefault(mid, set()).add(gid)

        fixed_defs = {g['bk_group_id']: g for g in PROPERTY_GROUPS}
        # 显示名单一来源：EXTRA_GROUP_DEFS（含 index）优先，再用 app.definitions.KNOWN_GROUP_NAMES
        # （CLI 与 migrate 共用，避免「ID->显示名」漂移），最后兜底为首字母大写的 group_id。
        name_by_id = {gid: d['bk_group_name'] for gid, d in EXTRA_GROUP_DEFS.items()}
        name_by_id.update(KNOWN_GROUP_NAMES)
        for model_id, groups in used_groups.items():
            for gid in groups:
                if (model_id, gid) in existing_groups:
                    continue
                # 先查通用分组定义，再查上游已知的非通用分组（auto/role/proc_port），
                # 都未命中再查 KNOWN_GROUP_NAMES，最后回退为「首字母大写的 group_id」
                spec = fixed_defs.get(gid) or EXTRA_GROUP_DEFS.get(gid)
                group_name = (
                    spec['bk_group_name'] if spec
                    else name_by_id.get(gid)
                    or gid[:1].upper() + gid[1:]
                )
                group_index = spec['bk_group_index'] if spec else 99
                # 此处仅处理 existing_groups 中不存在的分组（上面已 continue 跳过已存在的），
                # 属全新分组，省略 id 列交由 SQLite 自动取 MAX(id)+1。
                # 缺失分组补全（外置 SQL：migrate/insert_property_group.sql）
                self.execute_sql('migrate/insert_property_group.sql', {
                    '_id': f"{model_id}.{gid}",
                    'bk_obj_id': model_id,
                    'bk_group_id': gid,
                    'bk_group_name': group_name,
                    'bk_group_index': group_index,
                    'bk_isdefault': False,
                    'is_collapse': False,
                    'ispre': True
                })
                logger.info(f"补全分组定义: {model_id} / {gid} ({group_name})")

        logger.info(f"迁移了 {len(models) * len(PROPERTY_GROUPS)} 个固定属性分组（含缺失分组补全）")
    
    def update_attributes_group(self):
        """更新现有属性的分组"""
        # 构建 CASE WHEN 语句
        case_when_clauses = []
        params = {}
        
        for idx, (prop_id, group_id) in enumerate(PROPERTY_GROUP_UPDATE_MAP.items()):
            param_name = f"prop_{idx}"
            param_group = f"group_{idx}"
            case_when_clauses.append(f"WHEN bk_property_id = :{param_name} THEN :{param_group}")
            params[param_name] = prop_id
            params[param_group] = group_id
        
        if case_when_clauses:
            sql = f"""
                UPDATE cc_ObjAttDes 
                SET bk_property_group = CASE 
                    {' '.join(case_when_clauses)}
                    ELSE bk_property_group
                END
                WHERE bk_property_id IN ({', '.join([f':prop_{i}' for i in range(len(PROPERTY_GROUP_UPDATE_MAP))])})
            """
            
            # 执行更新
            self.execute_sql(sql, params)
            
            updated_count = len(PROPERTY_GROUP_UPDATE_MAP)
            logger.info(f"更新了 {updated_count} 个属性的分组")
    
    def create_hostbase_indexes(self):
        """创建 cc_HostBase 表索引（参考原项目 hostbase.go）
        
        注意：原项目使用 MongoDB 的 partialFilterExpression 创建部分唯一索引，
        只有满足特定条件（如 bk_host_innerip 不为空）的记录才需要满足唯一性。
        SQLite 不支持部分索引，因此将可能导致冲突的唯一索引改为普通索引。
        """
        indexes = [
            {
                "name": "bkcc_idx_bkHostInnerIP_bkCloudID",
                "columns": ["bk_host_innerip", "bk_cloud_id"],
                "unique": False
            },
            {
                "name": "bkcc_idx_bkHostInnerIPv6_bkCloudID",
                "columns": ["bk_host_inneripv6", "bk_cloud_id"],
                "unique": False
            },
            {
                "name": "bkcc_idx_bkAgentID",
                "columns": ["bk_agent_id"],
                "unique": False
            },
            {
                "name": "bkcc_idx_bk_cloud_inst_id",
                "columns": ["bk_cloud_inst_id"],
                "unique": False
            },
            {
                "name": "bkcc_idx_bk_supplier_account",
                "columns": ["bk_supplier_account"],
                "unique": False
            },
            {
                "name": "bkcc_idx_bk_cloud_id",
                "columns": ["bk_cloud_id"],
                "unique": False
            },
            {
                "name": "bkcc_idx_bk_os_type",
                "columns": ["bk_os_type"],
                "unique": False
            },
            {
                "name": "bkcc_idx_bk_asset_id",
                "columns": ["bk_asset_id"],
                "unique": False
            }
        ]
        
        for idx in indexes:
            unique_str = "UNIQUE" if idx["unique"] else ""
            columns_str = ", ".join(f'"{col}"' for col in idx["columns"])
            # MySQL 不支持 CREATE INDEX IF NOT EXISTS：先探测存在性再建，
            # 否则整段 DDL 报错被 except 吞成 warning → 索引（含唯一约束）静默丢失。
            if current_dialect() == 'mysql':
                if index_exists('cc_HostBase', idx['name']):
                    continue
                sql = f"CREATE {unique_str} INDEX {idx['name']} ON cc_HostBase ({columns_str})"
            else:
                sql = f"CREATE {unique_str} INDEX IF NOT EXISTS {idx['name']} ON cc_HostBase ({columns_str})"
            try:
                self.execute_sql(sql)
                logger.info(f"创建索引: {idx['name']}")
            except Exception as e:
                logger.warning(f"创建索引 {idx['name']} 失败: {e}")
    
    def create_module_host_config_indexes(self):
        """创建 cc_ModuleHostConfig 表索引（参考原项目 modulehostconfig.go）"""
        indexes = [
            {
                "name": "bkcc_idx_bkBizID_bkHostID",
                "columns": ["bk_biz_id", "bk_host_id"],
                "unique": False
            },
            {
                "name": "bkcc_idx_bk_module_id",
                "columns": ["bk_module_id"],
                "unique": False
            },
            {
                "name": "bkcc_idx_bk_set_id",
                "columns": ["bk_set_id"],
                "unique": False
            },
            {
                "name": "bkcc_idx_bk_module_id_bk_biz_id",
                "columns": ["bk_module_id", "bk_biz_id"],
                "unique": False
            },
            {
                "name": "bkcc_idx_bk_set_id_bk_biz_id",
                "columns": ["bk_set_id", "bk_biz_id"],
                "unique": False
            },
            {
                "name": "bkcc_unique_moduleID_hostID",
                "columns": ["bk_module_id", "bk_host_id"],
                "unique": True
            }
        ]
        
        for idx in indexes:
            unique_str = "UNIQUE" if idx["unique"] else ""
            columns_str = ", ".join(f'"{col}"' for col in idx["columns"])
            # 同 create_host_indexes：MySQL 需先探测存在性再建索引
            if current_dialect() == 'mysql':
                if index_exists('cc_ModuleHostConfig', idx['name']):
                    continue
                sql = f"CREATE {unique_str} INDEX {idx['name']} ON cc_ModuleHostConfig ({columns_str})"
            else:
                sql = f"CREATE {unique_str} INDEX IF NOT EXISTS {idx['name']} ON cc_ModuleHostConfig ({columns_str})"
            try:
                self.execute_sql(sql)
                logger.info(f"创建索引: {idx['name']}")
            except Exception as e:
                logger.warning(f"创建索引 {idx['name']} 失败: {e}")
    
    def init_core_tables(self):
        """初始化核心表结构"""
        core_tables_sql = {
            # 主线拓扑核心表（对应原项目 MongoDB collections）
            # 参考：/workspace/cmdb_server_lite/docs/原项目/bk-cmdb-主线拓扑与业务拓扑树分析.md
            "cc_ApplicationBase": """
                CREATE TABLE IF NOT EXISTS "cc_ApplicationBase" (
                    _id TEXT,
                    bk_biz_id INTEGER PRIMARY KEY,
                    bk_biz_name VARCHAR NOT NULL,
                    "default" INTEGER DEFAULT 0,
                    bk_supplier_account VARCHAR DEFAULT '0',
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    creator VARCHAR DEFAULT 'admin',
                    modifier VARCHAR DEFAULT 'admin'
                )
            """,
            "cc_SetBase": """
                CREATE TABLE IF NOT EXISTS "cc_SetBase" (
                    _id TEXT,
                    bk_set_id INTEGER PRIMARY KEY,
                    bk_set_name VARCHAR NOT NULL,
                    bk_parent_id INTEGER NOT NULL,
                    bk_biz_id INTEGER NOT NULL,
                    "default" INTEGER DEFAULT 0,
                    bk_set_desc VARCHAR,
                    bk_set_env VARCHAR DEFAULT '3',
                    bk_service_status VARCHAR DEFAULT '1',
                    bk_supplier_account VARCHAR DEFAULT '0',
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    creator VARCHAR DEFAULT 'admin',
                    modifier VARCHAR DEFAULT 'admin'
                )
            """,
            "cc_ModuleBase": """
                CREATE TABLE IF NOT EXISTS "cc_ModuleBase" (
                    _id TEXT,
                    bk_module_id INTEGER PRIMARY KEY,
                    bk_module_name VARCHAR NOT NULL,
                    bk_parent_id INTEGER NOT NULL,
                    bk_set_id INTEGER NOT NULL,
                    bk_biz_id INTEGER NOT NULL,
                    service_category_id INTEGER DEFAULT 0,
                    bk_module_type VARCHAR DEFAULT '1',
                    "default" INTEGER DEFAULT 0,
                    bk_supplier_account VARCHAR DEFAULT '0',
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    creator VARCHAR DEFAULT 'admin',
                    modifier VARCHAR DEFAULT 'admin'
                )
            """,
            "cc_HostBase": """
                CREATE TABLE IF NOT EXISTS "cc_HostBase" (
                    _id TEXT,
                    bk_host_id INTEGER PRIMARY KEY,
                    bk_host_name VARCHAR,
                    bk_host_innerip VARCHAR,
                    bk_host_outerip VARCHAR,
                    bk_host_inneripv6 VARCHAR,
                    bk_host_outeripv6 VARCHAR,
                    bk_cloud_id INTEGER DEFAULT 0,
                    bk_cloud_inst_id VARCHAR,
                    bk_agent_id VARCHAR,
                    bk_supplier_account VARCHAR DEFAULT '0',
                    operator VARCHAR,
                    bk_bak_operator VARCHAR,
                    bk_asset_id VARCHAR,
                    bk_sn VARCHAR,
                    bk_comment TEXT,
                    bk_service_term INTEGER,
                    bk_sla VARCHAR,
                    bk_state_name VARCHAR,
                    bk_province_name VARCHAR,
                    bk_isp_name VARCHAR,
                    bk_os_type VARCHAR,
                    bk_os_name VARCHAR,
                    bk_os_version VARCHAR,
                    bk_os_bit VARCHAR,
                    bk_cpu INTEGER,
                    bk_cpu_mhz INTEGER,
                    bk_cpu_module VARCHAR,
                    bk_mem INTEGER,
                    bk_disk INTEGER,
                    bk_mac VARCHAR,
                    bk_outer_mac VARCHAR,
                    import_from VARCHAR,
                    bk_verify_date DATE,
                    bk_verify_time TIME,
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    creator VARCHAR DEFAULT 'admin',
                    modifier VARCHAR DEFAULT 'admin'
                )
            """,
            "cc_ModuleHostConfig": """
                CREATE TABLE IF NOT EXISTS "cc_ModuleHostConfig" (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bk_biz_id INTEGER NOT NULL,
                    bk_host_id INTEGER NOT NULL,
                    bk_module_id INTEGER NOT NULL,
                    bk_set_id INTEGER NOT NULL,
                    bk_supplier_account VARCHAR DEFAULT '0',
                    UNIQUE(bk_host_id, bk_module_id)
                )
            """,
            "cc_ObjClassification": """
                CREATE TABLE IF NOT EXISTS "cc_ObjClassification" (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bk_classification_id VARCHAR NOT NULL UNIQUE,
                    bk_classification_name VARCHAR NOT NULL,
                    bk_classification_icon VARCHAR DEFAULT 'icon-cc-default',
                    ispre BOOLEAN DEFAULT false,
                    classification_index INTEGER DEFAULT 0,
                    bk_supplier_account VARCHAR DEFAULT '0'
                )
            """,
            "cc_ObjDes": """
                CREATE TABLE IF NOT EXISTS "cc_ObjDes" (
                    _id TEXT,
                    id INTEGER,
                    bk_obj_id VARCHAR NOT NULL PRIMARY KEY,
                    bk_obj_name VARCHAR NOT NULL,
                    bk_obj_icon VARCHAR DEFAULT 'icon-cc-default',
                    bk_classification_id VARCHAR,
                    ispre BOOLEAN DEFAULT false,
                    bk_ishidden BOOLEAN DEFAULT false,
                    bk_ispaused BOOLEAN DEFAULT false,
                    bk_isresourcedir BOOLEAN DEFAULT true,
                    obj_sort_number INTEGER DEFAULT 0,
                    creator VARCHAR DEFAULT 'admin',
                    modifier VARCHAR DEFAULT 'admin',
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bk_supplier_account VARCHAR DEFAULT '0'
                )
            """,
            "cc_PropertyGroup": """
                CREATE TABLE IF NOT EXISTS "cc_PropertyGroup" (
                    _id TEXT,
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bk_obj_id VARCHAR,
                    bk_group_id VARCHAR NOT NULL,
                    bk_group_name VARCHAR NOT NULL,
                    bk_group_index INTEGER DEFAULT 0,
                    bk_isdefault BOOLEAN DEFAULT false,
                    is_collapse BOOLEAN DEFAULT false,
                    ispre BOOLEAN DEFAULT false,
                    bk_biz_id INTEGER DEFAULT 0,
                    creator VARCHAR DEFAULT 'admin',
                    modifier VARCHAR DEFAULT 'admin',
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bk_supplier_account VARCHAR DEFAULT '0'
                )
            """,
            "cc_ObjAttDes": """
                CREATE TABLE IF NOT EXISTS "cc_ObjAttDes" (
                    _id TEXT,
                    id INTEGER,
                    bk_obj_id VARCHAR NOT NULL,
                    bk_property_id VARCHAR NOT NULL,
                    bk_property_name VARCHAR NOT NULL,
                    bk_property_type VARCHAR NOT NULL,
                    bk_property_group VARCHAR DEFAULT 'default',
                    isrequired BOOLEAN DEFAULT false,
                    bk_ispassword BOOLEAN DEFAULT false,
                    bk_ishidden BOOLEAN DEFAULT false,
                    isreadonly BOOLEAN DEFAULT false,
                    isonly BOOLEAN DEFAULT false,
                    editable BOOLEAN DEFAULT true,
                    bk_isapi BOOLEAN DEFAULT false,
                    bk_issystem BOOLEAN DEFAULT false,
                    ispre BOOLEAN DEFAULT false,
                    bk_property_index INTEGER DEFAULT 0,
                    ismultiple BOOLEAN DEFAULT false,
                    option TEXT,
                    placeholder VARCHAR,
                    unit VARCHAR,
                    creator VARCHAR DEFAULT 'admin',
                    modifier VARCHAR DEFAULT 'admin',
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bk_supplier_account VARCHAR DEFAULT '0',
                    PRIMARY KEY (bk_obj_id, bk_property_id)
                )
            """,
            "cc_AsstDes": """
                CREATE TABLE IF NOT EXISTS "cc_AsstDes" (
                    _id TEXT,
                    id INTEGER,
                    bk_asst_id VARCHAR NOT NULL PRIMARY KEY,
                    bk_asst_name VARCHAR NOT NULL,
                    bk_asst_icon VARCHAR DEFAULT 'icon-cc-default',
                    src_des VARCHAR DEFAULT '',
                    dest_des VARCHAR DEFAULT '',
                    -- direction 值域严格对齐上游 metadata.AssociationDirection：
                    -- none / src_to_dest / dest_to_src / bidirectional
                    -- （见 app/definitions.py VALID_ASST_DIRECTIONS）。
                    -- 缺省与上游 6 个预置关联类型一致（均为 src_to_dest）。
                    direction VARCHAR DEFAULT 'src_to_dest',
                    ispre BOOLEAN DEFAULT false,
                    creator VARCHAR DEFAULT 'admin',
                    modifier VARCHAR DEFAULT 'admin',
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bk_supplier_account VARCHAR DEFAULT '0'
                )
            """,
            "cc_ObjAsst": """
                CREATE TABLE IF NOT EXISTS "cc_ObjAsst" (
                    _id TEXT,
                    id INTEGER,
                    bk_obj_id VARCHAR NOT NULL,
                    target_obj_id VARCHAR NOT NULL,
                    target_obj_name VARCHAR NOT NULL,
                    bk_asst_id VARCHAR NOT NULL,
                    bk_obj_asst_id VARCHAR NOT NULL PRIMARY KEY,
                    bk_obj_asst_name VARCHAR NOT NULL,
                    mapping VARCHAR,
                    on_delete VARCHAR,
                    creator VARCHAR DEFAULT 'admin',
                    modifier VARCHAR DEFAULT 'admin',
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bk_supplier_account VARCHAR DEFAULT '0'
                )
            """,
            # 兼容性单表（已废弃，实际使用按模型分表 cc_InstAsst_0_pub_{obj_id}）
            # 保留此表用于旧版本数据迁移和历史兼容，新业务逻辑请勿使用
            "cc_InstAsst_0_pub": """
                CREATE TABLE IF NOT EXISTS "cc_InstAsst_0_pub" (
                    _id TEXT,
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bk_obj_id VARCHAR NOT NULL,
                    bk_inst_id INTEGER NOT NULL,
                    bk_asst_obj_id VARCHAR NOT NULL,
                    bk_asst_inst_id INTEGER NOT NULL,
                    bk_obj_asst_id VARCHAR NOT NULL,
                    bk_relation_type_id VARCHAR NOT NULL,
                    bk_supplier_account VARCHAR DEFAULT '0'
                )
            """,
            # 实例关联分表（动态创建，格式: cc_InstAsst_0_pub_{obj_id}，与原项目保持一致）
            # 详见 create_instance_association_table() 方法
            "cc_ObjectUnique": """
                CREATE TABLE IF NOT EXISTS "cc_ObjectUnique" (
                    _id TEXT,
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bk_template_id INTEGER DEFAULT 0,
                    bk_obj_id VARCHAR NOT NULL,
                    keys TEXT,
                    ispre BOOLEAN DEFAULT false,
                    bk_supplier_account VARCHAR DEFAULT '0',
                    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "user_custom": """
                CREATE TABLE IF NOT EXISTS "user_custom" (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name VARCHAR NOT NULL,
                    config_key VARCHAR NOT NULL,
                    config_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bk_supplier_account VARCHAR DEFAULT '0',
                    UNIQUE(user_name, config_key, bk_supplier_account)
                )
            """,
        }
        
        for table_name, create_sql in core_tables_sql.items():
            self.execute_sql(create_sql)
            logger.info(f"初始化核心表: {table_name}")

        # 兼容旧库：补齐资源目录标记列（已有 cc_ObjDes 无该列时补足，避免重跑 migrate 失败）
        self._ensure_objdes_resdir_column()

    def _ensure_objdes_resdir_column(self):
        """幂等补齐 cc_ObjDes.bk_isresourcedir 列（老库重跑迁移时不报错）

        bk_isresourcedir 控制模型是否出现在「资源目录」：1=展示，0=不展示。
        业务 biz 默认在资源目录展示（与 BUILTIN_MODELS 中 biz.bk_isresourcedir=1 一致），
        因此无论老库是否已存在该列，都确保 biz 该行收敛为 1。
        """
        # 跨库内省取代 SQLite 专用语法：PRAGMA table_info 在 MySQL / PostgreSQL 均不存在
        columns = get_column_names('cc_ObjDes')
        if 'bk_isresourcedir' not in columns:
            self.execute_sql(
                'ALTER TABLE cc_ObjDes ADD COLUMN bk_isresourcedir BOOLEAN DEFAULT 1'
            )
            logger.info("补齐 cc_ObjDes 列: bk_isresourcedir")
        # 业务 biz 默认在资源目录展示（覆盖旧库历史值 0、新增列默认 1 均收敛为 1）
        self.execute_sql("UPDATE cc_ObjDes SET bk_isresourcedir = 1 WHERE bk_obj_id = 'biz'")
    
    def migrate_models(self):
        """迁移模型数据"""
        ui_project = self.workspace_root / "cmdb_ui_lite" / "src" / "assets" / "api"
        index_path = ui_project / "index.json"
        
        if not index_path.exists():
            logger.warning(f"找不到模型数据文件: {index_path}")
            return
        
        with open(index_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 模型表 upsert：冲突键 bk_obj_id（cc_ObjDes 主键），resource dir 恒为 1。
        sql = self.upsert_sql(
            'cc_ObjDes', self.OBJDES_COLUMNS, conflict='bk_obj_id',
            literals={**self.OBJDES_LITERALS, 'bk_isresourcedir': '1'},
        )
        for idx, model in enumerate(data.get("models", [])):
            model_id = model.get("bk_obj_id")
            classification_id = MODEL_CLASSIFICATION_MAP.get(model_id, "bk_uncategorized")

            self.execute_sql(sql, {
                '_id': model_id,
                'id': idx + 1,
                'bk_obj_id': model_id,
                'bk_obj_name': model.get("bk_obj_name"),
                'bk_obj_icon': model.get("bk_obj_icon") or DEFAULT_OBJ_ICON,
                'bk_classification_id': classification_id,
                'ispre': True,
                'obj_sort_number': idx
            })

        logger.info(f"迁移了 {len(data.get('models', []))} 个模型")
    
    def migrate_builtin_models(self):
        """迁移内置模型（biz/set/module）到 cc_ObjDes"""
        # 与 migrate_models 共用列清单，差别仅在 bk_isresourcedir 走绑定参数
        # （内置模型逐个指定，普通模型恒为 1）。
        sql = self.upsert_sql(
            'cc_ObjDes', self.OBJDES_COLUMNS, conflict='bk_obj_id',
            literals=self.OBJDES_LITERALS,
        )
        for model in BUILTIN_MODELS:
            model_id = model["bk_obj_id"]
            self.execute_sql(sql, {
                '_id': model_id,
                'id': model["obj_sort_number"] + 100,
                'bk_obj_id': model_id,
                'bk_obj_name': model["bk_obj_name"],
                'bk_obj_icon': model["bk_obj_icon"],
                'bk_classification_id': model["bk_classification_id"],
                'ispre': model["ispre"],
                'obj_sort_number': model["obj_sort_number"],
                'bk_isresourcedir': model.get("bk_isresourcedir", 1)
            })
        logger.info(f"迁移了 {len(BUILTIN_MODELS)} 个内置模型")
    
    def migrate_builtin_model_attributes(self):
        """迁移内置模型的属性定义到 cc_ObjAttDes"""
        attr_id = 10000
        total_attrs = 0
        
        sql = self.upsert_sql(
            'cc_ObjAttDes', self.OBJATTDES_COLUMNS,
            conflict=self.OBJATTDES_CONFLICT, literals=self.OBJATTDES_LITERALS,
        )
        for model_id, attributes in BUILTIN_MODEL_ATTRIBUTES.items():
            for attr in attributes:
                prop_type = attr.get("bk_property_type", "singlechar")
                option = attr.get("option")
                option = self.process_option(prop_type, option)

                self.execute_sql(sql, {
                    '_id': f"{model_id}.{attr['bk_property_id']}",
                    'id': attr_id,
                    'bk_obj_id': model_id,
                    'bk_property_id': attr['bk_property_id'],
                    'bk_property_name': attr['bk_property_name'],
                    'bk_property_type': prop_type,
                    'bk_property_group': attr['bk_property_group'],
                    'isrequired': attr['isrequired'],
                    'bk_ispassword': attr.get('bk_ispassword', False),
                    'bk_ishidden': attr['bk_ishidden'],
                    'isreadonly': attr['isreadonly'],
                    'isonly': attr['isonly'],
                    'bk_isapi': attr['bk_isapi'],
                    'bk_issystem': attr['bk_issystem'],
                    'option': option,
                    'unit': attr.get('unit', ''),
                    'placeholder': attr.get('placeholder', ''),
                    'editable': attr['editable'],
                    'ispre': attr['ispre'],
                    'bk_property_index': attr['bk_property_index']
                })
                attr_id += 1
                total_attrs += 1
        
        logger.info(f"迁移了 {total_attrs} 个内置模型属性")

    def ensure_builtin_time_attributes(self):
        """为 host 与通用普通模型补齐内置时间属性（创建时间 / 最后修改时间）

        与 biz/set/module 同规则（BUILTIN_MODEL_ATTRIBUTES）：ispre + 只读 + 页面可见。
        覆盖三类模型来源：
          1) JSON 资源迁移出来的模型（host / bk_switch / bk_slb...）——已由
             migrate_attributes 走 SYSTEM_PROPERTIES 写入，这里做兜底校正；
          2) CLI（cmdb model create / scaffold apply）在本方法上线前建的历史模型；
          3) 存量数据库直接升级（无需清库重跑）。

        幂等：cc_ObjAttDes 主键为 (bk_obj_id, bk_property_id)，重复执行只刷新定义；
        同时校验实例表是否具备 create_time / last_time 列，缺失则 ALTER 补列。
        biz/set/module 由 BUILTIN_MODEL_ATTRIBUTES 单独维护，此处跳过。
        """
        topo_model_ids = {m["bk_obj_id"] for m in BUILTIN_MODELS}
        models = self.execute_query('migrate/select_all_model_ids.sql')

        max_row = self.execute_query('migrate/select_max_attribute_id.sql')
        next_id = ((max_row[0].get('max_id') if max_row else None) or 0) + 1

        touched_attrs = 0
        added_columns = []
        attr_upsert_sql = self.upsert_sql(
            'cc_ObjAttDes', self.OBJATTDES_COLUMNS,
            conflict=self.OBJATTDES_CONFLICT, literals=self.OBJATTDES_LITERALS,
        )

        for model in models:
            model_id = model['bk_obj_id']
            if model_id in topo_model_ids:
                continue

            for tp in BUILTIN_TIME_PROPERTIES:
                prop_id = tp['bk_property_id']
                existing = self.execute_query(
                    'migrate/select_attribute_id.sql',
                    {'bk_obj_id': model_id, 'bk_property_id': prop_id}
                )
                if existing and existing[0].get('id'):
                    attr_id = existing[0]['id']
                else:
                    attr_id = next_id
                    next_id += 1

                self.execute_sql(attr_upsert_sql, {
                    '_id': f"{model_id}.{prop_id}",
                    'id': attr_id,
                    'bk_obj_id': model_id,
                    'bk_property_id': prop_id,
                    'bk_property_name': tp['bk_property_name'],
                    'bk_property_type': tp['bk_property_type'],
                    'bk_property_group': tp['bk_property_group'],
                    'isrequired': tp['isrequired'],
                    'bk_ispassword': tp['bk_ispassword'],
                    'bk_ishidden': tp['bk_ishidden'],
                    'isreadonly': tp['isreadonly'],
                    'isonly': tp['isonly'],
                    'bk_isapi': tp['bk_isapi'],
                    'bk_issystem': tp['bk_issystem'],
                    'option': None,
                    'unit': tp['unit'],
                    'placeholder': tp['placeholder'],
                    'editable': tp['editable'],
                    'ispre': tp['ispre'],
                    'bk_property_index': tp['bk_property_index'],
                })
                touched_attrs += 1

            # 实例表补列（host 用 cc_HostBase，通用模型用分表）
            table_name = 'cc_HostBase' if model_id == 'host' \
                else f"cc_ObjectBase_0_pub_{model_id}"
            try:
                cols = {c for c in get_column_names(table_name)}
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"跳过实例表列校验 {table_name}: {exc}")
                continue
            if not cols:
                continue
            for prop_id in ('create_time', 'last_time'):
                if prop_id not in cols:
                    self.execute_sql(
                        f'ALTER TABLE "{table_name}" ADD COLUMN {prop_id} '
                        f'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
                    )
                    added_columns.append(f"{table_name}.{prop_id}")

        logger.info(
            f"内置时间属性补齐完成：写入 {touched_attrs} 条属性定义"
            + (f"，补列 {added_columns}" if added_columns else "")
        )

    def process_option(self, prop_type, option):
        """
        处理属性选项值，根据类型进行转换
        
        Args:
            prop_type: 属性类型
            option: 原始选项值
        
        Returns:
            处理后的选项值（JSON字符串或原值）
        """
        if option is None:
            return None
        
        # 如果已经是字符串，直接返回
        if isinstance(option, str):
            return option
        
        # 枚举类型（单选）
        if prop_type == 'enum':
            if isinstance(option, list):
                # 已是标准结构（元素为 {"id":..,"name":..}）时原样存储，
                # 避免 convert_enum_option 把 dict 当字符串再序列化导致嵌套字符串化。
                if self._is_structured_enum(option):
                    return json.dumps(option, ensure_ascii=False)
                # 简单字符串数组（如 ["Linux","Windows"]）转换为原项目标准格式
                return convert_enum_option(option)
            return option

        # 多选枚举类型
        if prop_type == 'enummulti':
            if isinstance(option, list):
                if self._is_structured_enum(option):
                    return json.dumps(option, ensure_ascii=False)
                return convert_enum_option(option)
            return option

        # 列表类型
        if prop_type == 'list':
            if isinstance(option, list):
                # 元素为字符串时直接序列化（["北京","上海"]）；
                # 元素为对象（极少见）时按原项目 list 规范提取为字符串数组。
                if option and isinstance(option[0], dict):
                    str_list = [str(o.get('name', o.get('id', ''))) for o in option]
                    return json.dumps(str_list, ensure_ascii=False)
                return json.dumps(option, ensure_ascii=False)
            return option
        
        # 整数范围类型
        if prop_type == 'int':
            if isinstance(option, dict):
                return json.dumps(option, ensure_ascii=False)
            return option
        
        # 浮点数范围类型
        if prop_type == 'float':
            if isinstance(option, dict):
                return json.dumps(option, ensure_ascii=False)
            return option
        
        # 其他类型转为JSON字符串
        return json.dumps(option, ensure_ascii=False)

    @staticmethod
    def _is_structured_enum(option_list):
        """
        判断枚举选项是否已是原项目标准结构（元素为 {"id":..,"name":..} 对象）。
        用于兼容 host 等模型中 source option 已是结构化 dict 的情况，
        避免 convert_enum_option 将其当纯字符串再次序列化造成嵌套字符串化。
        """
        if not isinstance(option_list, list) or len(option_list) == 0:
            return False
        return all(
            isinstance(item, dict) and 'id' in item and 'name' in item
            for item in option_list
        )

    def migrate_attributes(self):
        """迁移属性数据"""
        ui_project = self.workspace_root / "cmdb_ui_lite" / "src" / "assets" / "api"
        index_path = ui_project / "index.json"
        
        if not index_path.exists():
            logger.warning(f"找不到模型数据文件: {index_path}")
            return
        
        with open(index_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        attr_id = 1
        total_attrs = 0
        
        for model in data.get("models", []):
            model_id = model.get("bk_obj_id")
            attr_file_path = ui_project / "models" / "attributes" / f"{model_id}.json"
            
            try:
                with open(attr_file_path, 'r', encoding='utf-8') as f:
                    attr_data = json.load(f)
                
                properties = attr_data.get("info", [])
                
                logger.info(f"插入模型 {model_id} 的 {len(SYSTEM_PROPERTIES)} 个系统属性")
                
                # 先插入系统属性
                for sys_prop in SYSTEM_PROPERTIES:
                    # host 模型在上游仅用 bk_host_name 作名称字段，不注册 bk_inst_name；
                    # 对齐上游：跳过 host 的 bk_inst_name，避免 host 出现双名称字段。
                    if model_id == 'host' and sys_prop['bk_property_id'] == 'bk_inst_name':
                        continue
                    prop_type = sys_prop.get("bk_property_type", "singlechar")
                    option = sys_prop.get("option")
                    option = self.process_option(prop_type, option)
                    
                    # 系统属性写入（外置列集 OBJATTDES_COLUMNS，复合主键 upsert）
                    self.execute_sql(
                        self.upsert_sql('cc_ObjAttDes', self.OBJATTDES_COLUMNS,
                                       conflict=self.OBJATTDES_CONFLICT,
                                       literals=self.OBJATTDES_LITERALS), {
                        '_id': f"{model_id}.{sys_prop['bk_property_id']}",
                        'id': attr_id,
                        'bk_obj_id': model_id,
                        'bk_property_id': sys_prop['bk_property_id'],
                        'bk_property_name': sys_prop['bk_property_name'],
                        'bk_property_type': prop_type,
                        'bk_property_group': sys_prop['bk_property_group'],
                        'isrequired': sys_prop['isrequired'],
                        'bk_ispassword': sys_prop['bk_ispassword'],
                        'bk_ishidden': sys_prop['bk_ishidden'],
                        'isreadonly': sys_prop['isreadonly'],
                        'isonly': sys_prop['isonly'],
                        'bk_isapi': sys_prop['bk_isapi'],
                        'bk_issystem': sys_prop['bk_issystem'],
                        'option': option,
                        'unit': sys_prop['unit'],
                        'placeholder': sys_prop['placeholder'],
                        'editable': sys_prop['editable'],
                        'ispre': sys_prop['ispre'],
                        'bk_property_index': sys_prop['bk_property_index']
                    })
                    attr_id += 1
                    total_attrs += 1
                
                # 再插入业务属性
                for prop in properties:
                    bk_property_id = prop.get("bk_property_id")
                    
                    if bk_property_id in SYSTEM_FIELDS:
                        continue
                    
                    prop_type = prop.get("bk_property_type", "singlechar")
                    option = prop.get("option")
                    option = self.process_option(prop_type, option)
                    
                    # 判断是否为多选枚举
                    is_multiple = prop_type == 'enummulti'
                    
                    bk_issystem = prop.get("bk_issystem", False)
                    bk_isapi = prop.get("bk_isapi", False)
                    isreadonly = prop.get("isreadonly", False)
                    isonly = prop.get("isonly", False)
                    editable = prop.get("editable", True)
                    bk_ishidden = prop.get("bk_ishidden", False)

                    # 业务属性写入（含 ismultiple 列，复合主键 upsert）
                    self.execute_sql(
                        self.upsert_sql('cc_ObjAttDes', self.OBJATTDES_COLUMNS_WITH_MULTI,
                                       conflict=self.OBJATTDES_CONFLICT,
                                       literals=self.OBJATTDES_LITERALS), {
                        '_id': f"{model_id}.{bk_property_id}",
                        'id': attr_id,
                        'bk_obj_id': model_id,
                        'bk_property_id': bk_property_id,
                        'bk_property_name': prop.get("bk_property_name"),
                        'bk_property_type': prop_type,
                        'bk_property_group': prop.get("bk_property_group", "default"),
                        'isrequired': prop.get("isrequired", False),
                        'bk_ispassword': prop.get("bk_ispassword", False),
                        'bk_ishidden': bk_ishidden,
                        'isreadonly': isreadonly,
                        'isonly': isonly,
                        'bk_isapi': bk_isapi,
                        'bk_issystem': bk_issystem,
                        'ismultiple': is_multiple,
                        'option': option,
                        'unit': prop.get("unit"),
                        'placeholder': prop.get("placeholder"),
                        'editable': editable,
                        'ispre': prop.get("ispre", False),
                        'bk_property_index': prop.get("bk_property_index", 0)
                    })
                    attr_id += 1
                    total_attrs += 1
                
                logger.info(f"迁移模型 {model_id} 的 {len(properties) + len(SYSTEM_PROPERTIES)} 个属性")
            except FileNotFoundError:
                logger.warning(f"警告：未找到属性文件 {attr_file_path}")
        
        logger.info(f"总共迁移 {total_attrs} 个属性")
    
    def create_instance_table(self, model_id):
        """为模型创建实例表和实例关联分表"""
        table_name = f"cc_ObjectBase_0_pub_{model_id}"
        
        # 先查询模型的属性定义
        attributes = self.execute_query("""
            SELECT bk_property_id, bk_property_type
            FROM cc_ObjAttDes 
            WHERE bk_obj_id = :model_id AND bk_property_id NOT IN ('id', 'bk_inst_id', 'bk_inst_name', 'bk_obj_id')
            ORDER BY bk_property_index
        """, {"model_id": model_id})
        
        # 构建表结构
        columns = [
            '_id TEXT',
            'id INTEGER PRIMARY KEY AUTOINCREMENT',
            'bk_inst_id INTEGER NOT NULL',
            'bk_inst_name VARCHAR NOT NULL',
            'bk_supplier_account VARCHAR DEFAULT \'0\'',
            'bk_obj_id VARCHAR NOT NULL',
            'create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'bk_operate_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'creator VARCHAR DEFAULT \'\''
        ]
        
        # 添加模型自定义属性
        for attr in attributes:
            prop_id = attr['bk_property_id']
            prop_type = attr['bk_property_type']

            if prop_id in SYSTEM_FIELDS:
                continue

            # 关联类型（singleasst/multiasst/foreignkey）：与原 Go 项目一致，
            # 不作为实例表物理列，关联数据存于 cc_InstAsst 分表，直接跳过。
            if prop_type in ASSOCIATION_PROPERTY_TYPES:
                continue

            # lite 历史命名（如 user）先归一为 Go 类型（objuser）再映射。
            prop_type = LEGACY_PROPERTY_TYPE_ALIAS.get(prop_type, prop_type)

            # 其余必须是 Go definitions.go 的 16 种合法类型，未知类型直接抛错。
            sql_type = get_sql_type(prop_type)
            columns.append(f'"{prop_id}" {sql_type}')
        
        create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(columns)})'
        self.execute_sql(create_sql)
        logger.info(f"创建实例表: {table_name}")
        
        # 同时创建实例关联分表（与原项目保持一致）
        self.create_instance_association_table(model_id)
    
    def create_instance_association_table(self, model_id):
        """
        为模型创建实例关联分表
        格式: cc_InstAsst_0_pub_{obj_id}
        与原项目 tablenames.go GetObjectInstAsstTableName 一致
        """
        asst_table_name = f"cc_InstAsst_0_pub_{model_id}"
        
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS "{asst_table_name}" (
                _id TEXT,
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bk_obj_id VARCHAR NOT NULL,
                bk_inst_id INTEGER NOT NULL,
                bk_asst_obj_id VARCHAR NOT NULL,
                bk_asst_inst_id INTEGER NOT NULL,
                bk_obj_asst_id VARCHAR NOT NULL,
                bk_relation_type_id VARCHAR NOT NULL,
                bk_supplier_account VARCHAR DEFAULT '0'
            )
        """
        self.execute_sql(create_sql)
        logger.info(f"创建实例关联分表: {asst_table_name}")
    
    def migrate_instances(self):
        """迁移实例数据"""
        ui_project = self.workspace_root / "cmdb_ui_lite" / "src" / "assets" / "api"
        
        with open(ui_project / "index.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for model in data["models"]:
            model_id = model.get("bk_obj_id")
            
            if model_id == "host":
                logger.info(f"跳过 host 模型实例迁移（由 migrate_mainline_topo 统一管理）")
                continue
                
            table_name = f"cc_ObjectBase_0_pub_{model_id}"
            inst_file_path = ui_project / "models" / "instances" / f"{model_id}.json"
            
            try:
                with open(inst_file_path, 'r', encoding='utf-8') as f:
                    inst_data = json.load(f)
                
                instances = inst_data.get("info", [])
                
                # 先获取模型的属性定义，用于正确处理数据类型
                attributes = self.execute_query("""
                    SELECT bk_property_id, bk_property_type FROM cc_ObjAttDes WHERE bk_obj_id = :model_id
                """, {"model_id": model_id})
                attr_type_map = {
                    attr['bk_property_id']: attr['bk_property_type']
                    for attr in attributes
                }
                
                logger.info(f"迁移模型 {model_id} 的 {len(instances)} 个实例")
                
                for idx, inst in enumerate(instances):
                    columns = []
                    placeholders = []
                    values = []
                    
                    inst_id = inst.get("id", idx + 1)
                    bk_inst_id = inst.get("bk_inst_id", inst_id)
                    bk_inst_name = inst.get("bk_inst_name", "")
                    
                    if not bk_inst_name and "name" in inst:
                        bk_inst_name = inst["name"]
                    elif not bk_inst_name and "bk_lb_name" in inst:
                        bk_inst_name = inst["bk_lb_name"]
                    elif not bk_inst_name and "bk_host_innerip" in inst:
                        bk_inst_name = inst["bk_host_innerip"]
                    elif not bk_inst_name and "bk_server_name" in inst:
                        bk_inst_name = inst["bk_server_name"]
                    elif not bk_inst_name and "bk_listener_name" in inst:
                        bk_inst_name = inst["bk_listener_name"]
                    elif not bk_inst_name and "bk_switch_name" in inst:
                        bk_inst_name = inst["bk_switch_name"]
                    
                    # 添加必要字段
                    if inst_id:
                        columns.append("id")
                        placeholders.append(":id")
                        values.append(inst_id)
                    if bk_inst_id:
                        columns.append("bk_inst_id")
                        placeholders.append(":bk_inst_id")
                        values.append(bk_inst_id)
                    if bk_inst_name:
                        columns.append("bk_inst_name")
                        placeholders.append(":bk_inst_name")
                        values.append(bk_inst_name)
                    
                    # 添加其他字段
                    for key, value in inst.items():
                        if key not in ["id", "bk_inst_id", "bk_inst_name"]:
                            columns.append(f'"{key}"')
                            placeholders.append(f":{key}")
                            # 根据属性类型处理值
                            prop_type = attr_type_map.get(key)
                            # organization（部门 ID 数组）按 JSON 文本落库，与 MongoDB 数组结构一致；
                            # objuser 为纯逗号拼接字符串（非数组），走 else 原样保存为字符串。
                            if prop_type == 'organization' and isinstance(value, (list, dict)):
                                values.append(json.dumps(value, ensure_ascii=False))
                            elif prop_type in ['list', 'enum', 'enummulti', 'array', 'object'] and isinstance(value, (list, dict)):
                                values.append(json.dumps(value, ensure_ascii=False))
                            else:
                                values.append(value)
                    
                    if columns:
                        columns.append("bk_obj_id")
                        placeholders.append(":bk_obj_id")
                        values.append(model_id)
                        
                        columns.append("bk_supplier_account")
                        placeholders.append(":bk_supplier_account")
                        values.append("0")
                        
                        # 构建参数字典
                        params = {}
                        for col, val in zip([c.strip('"') for c in columns], values):
                            params[col] = val
                        
                        # 动态实例分表 upsert：表名/列集运行期确定，冲突键取实例表主键 id。
                        # 改走 dialect.upsert 生成三库通用幂等语句，不再硬编码 SQLite 专属语法。
                        sql = upsert(table_name, [c.strip('"') for c in columns],
                                     placeholders, conflict='id')
                        self.execute_sql(sql, params)
                
            except FileNotFoundError:
                logger.warning(f"未找到实例文件 {inst_file_path}")
    
    def migrate_associations(self):
        """迁移关联关系数据"""
        ui_project = self.workspace_root / "cmdb_ui_lite" / "src" / "assets" / "api"

        # 1. 预置关联类型（cc_AsstDes）—— 数据见 seeds.ASSOCIATION_KIND_SEEDS
        #
        # 幂等写法说明：此处经 dialect.upsert 生成三库通用的 Upsert，冲突键取
        # bk_asst_id（业务唯一键）而非自增 id。原实现是硬编码 SQLite 专属的
        # `INSERT OR REPLACE`，虽有 adapt_sql 正则兜底改写，但兜底依赖
        # dialect._CONFLICT_MAP 的表名映射（冲突键藏在方言层，改表结构时容易漏改），
        # 且正则以 `[^)]*` 匹配列/值，值中一旦出现函数调用括号就会截断。
        # 显式 upsert 把冲突键留在调用处，语义自证、三库一致。
        asst_upsert_sql = self.upsert_sql(
            'cc_AsstDes',
            ['id', 'bk_asst_id', 'bk_asst_name', 'bk_asst_icon', 'src_des',
             'dest_des', 'direction', 'ispre', 'bk_supplier_account',
             'creator', 'modifier'],
            conflict='bk_asst_id',
            literals={'creator': "'admin'", 'modifier': "'admin'"},
        )
        for idx, asst_type in enumerate(ASSOCIATION_KIND_SEEDS, 1):
            self.execute_sql(asst_upsert_sql, {
                "id": idx,
                "bk_asst_id": asst_type["bk_asst_id"],
                "bk_asst_name": asst_type["bk_asst_name"],
                "bk_asst_icon": asst_type.get("bk_asst_icon") or DEFAULT_ASST_ICON,
                "src_des": asst_type["src_des"],
                "dest_des": asst_type["dest_des"],
                # 种子里的 direction 已是常量引用，此处再过一次归一，
                # 使"种子被手工改坏"也无法把非法值写进库（防御性，正常路径无副作用）。
                "direction": normalize_asst_direction(asst_type["direction"]),
                "ispre": asst_type["ispre"],
                "bk_supplier_account": asst_type["bk_supplier_account"]
            })

        logger.info(f"迁移了 {len(ASSOCIATION_KIND_SEEDS)} 个关联类型")

        # 2. 预置模型关联（cc_ObjAsst）—— 数据见 seeds.OBJECT_ASSOCIATION_SEEDS
        # 冲突键取 bk_obj_asst_id（业务唯一键：{源}_{类型}_{目标}）。
        obj_asst_upsert_sql = self.upsert_sql(
            'cc_ObjAsst',
            ['id', 'bk_obj_id', 'target_obj_id', 'target_obj_name', 'bk_asst_id',
             'bk_obj_asst_id', 'bk_obj_asst_name', 'mapping', 'on_delete',
             'creator', 'modifier', 'bk_supplier_account'],
            conflict='bk_obj_asst_id',
            literals={'creator': "'admin'", 'modifier': "'admin'"},
        )
        for idx, obj_asst in enumerate(OBJECT_ASSOCIATION_SEEDS, 1):
            self.execute_sql(obj_asst_upsert_sql, {
                "id": idx,
                "bk_obj_id": obj_asst["bk_obj_id"],
                "target_obj_id": obj_asst["target_obj_id"],
                "target_obj_name": obj_asst["target_obj_name"],
                "bk_asst_id": obj_asst["bk_asst_id"],
                "bk_obj_asst_id": obj_asst["bk_obj_asst_id"],
                "bk_obj_asst_name": obj_asst["bk_obj_asst_name"],
                "mapping": obj_asst["mapping"],
                "on_delete": obj_asst["on_delete"],
                "bk_supplier_account": obj_asst["bk_supplier_account"]
            })

        logger.info(f"迁移了 {len(OBJECT_ASSOCIATION_SEEDS)} 个对象关联")

        # 3. 创建所有模型的实例关联分表（在迁移数据前）
        self._ensure_all_inst_asst_tables_exist()

        # 4. 迁移实例关联数据（按模型分表，与原项目保持一致）
        inst_assoc_file = ui_project / "models" / "associations" / "index.json"
        if inst_assoc_file.exists():
            with open(inst_assoc_file, 'r', encoding='utf-8') as f:
                inst_assoc_data = json.load(f)
            
            associations = inst_assoc_data.get("associations", [])
            
            from app.service.instance_service import InstanceService
            skipped = 0
            for assoc in associations:
                # 确定 bk_obj_asst_id 和 bk_relation_type_id
                # 格式: {源模型ID}_{AsstKindID}_{目标模型ID}
                # 例如: bk_slb_default_bk_slb_server
                bk_obj_id = assoc.get("bk_obj_id")
                bk_asst_obj_id = assoc.get("bk_asst_obj_id")
                # bk_relation_type_id 现在使用标准 bk_asst_id (default)
                bk_relation_type_id = assoc.get("bk_relation_type_id")
                # bk_obj_asst_id 格式: {源}_{类型}_{目标}
                bk_obj_asst_id = f"{bk_obj_id}_{bk_relation_type_id}_{bk_asst_obj_id}"

                # 遵循原项目 bk-cmdb 逻辑：两端实例必须存在才允许创建关联，
                # 跳过指向不存在实例的孤儿关联（种子数据不一致时的防护）。
                if not InstanceService.get_instance(bk_obj_id, assoc.get("bk_inst_id")):
                    logger.warning(f"跳过孤儿关联（源实例不存在）: {bk_obj_id}/{assoc.get('bk_inst_id')} -> {bk_asst_obj_id}/{assoc.get('bk_asst_inst_id')}")
                    skipped += 1
                    continue
                if not InstanceService.get_instance(bk_asst_obj_id, assoc.get("bk_asst_inst_id")):
                    logger.warning(f"跳过孤儿关联（目标实例不存在）: {bk_obj_id}/{assoc.get('bk_inst_id')} -> {bk_asst_obj_id}/{assoc.get('bk_asst_inst_id')}")
                    skipped += 1
                    continue

                assoc_data = {
                    "id": assoc.get("id"),
                    "bk_obj_id": bk_obj_id,
                    "bk_inst_id": assoc.get("bk_inst_id"),
                    "bk_asst_obj_id": bk_asst_obj_id,
                    "bk_asst_inst_id": assoc.get("bk_asst_inst_id"),
                    "bk_obj_asst_id": bk_obj_asst_id,
                    "bk_relation_type_id": bk_relation_type_id,
                    "bk_supplier_account": "0"
                }

                # 按源模型和目标模型分表插入（与原项目一致）
                self._insert_instance_association_to_sharding_tables(assoc_data)

            if skipped:
                logger.warning(f"已跳过 {skipped} 条孤儿关联（源/目标实例不存在）")
            
            logger.info(f"迁移了 {len(associations)} 个实例关联")
        else:
            logger.warning("未找到实例关联数据文件")
        
        # 4. 添加模拟的 host_install_slb 实例关联数据 (mapping: 1:1)
        # 模拟主机 1 安装了 SLB 实例 1
        mock_host_slb_associations = [
            {
                "id": 117,
                "bk_obj_id": "host",
                "bk_inst_id": 1,
                "bk_asst_obj_id": "bk_slb",
                "bk_asst_inst_id": 1,
                "bk_obj_asst_id": "host_install_slb",
                "bk_relation_type_id": "install",
                "bk_supplier_account": "0"
            },
            {
                "id": 118,
                "bk_obj_id": "host",
                "bk_inst_id": 2,
                "bk_asst_obj_id": "bk_slb",
                "bk_asst_inst_id": 2,
                "bk_obj_asst_id": "host_install_slb",
                "bk_relation_type_id": "install",
                "bk_supplier_account": "0"
            }
        ]
        
        for assoc in mock_host_slb_associations:
            self._insert_instance_association_to_sharding_tables(assoc)
        
        logger.info(f"添加了 {len(mock_host_slb_associations)} 个模拟主机-SLB实例关联")

    def _insert_instance_association_to_sharding_tables(self, assoc_data):
        """
        将实例关联数据插入到源模型和目标模型的分表
        与原项目 instance.go save() 方法保持一致
        """
        bk_obj_id = assoc_data.get("bk_obj_id")
        bk_asst_obj_id = assoc_data.get("bk_asst_obj_id")
        
        # 插入到源模型的关联分表
        src_table = f"cc_InstAsst_0_pub_{bk_obj_id}"
        self._insert_association_to_table(src_table, assoc_data)
        
        # 如果源模型和目标模型不同，同时插入到目标模型的关联分表
        if bk_obj_id != bk_asst_obj_id:
            dst_table = f"cc_InstAsst_0_pub_{bk_asst_obj_id}"
            self._insert_association_to_table(dst_table, assoc_data)

    def _insert_association_to_table(self, table_name, assoc_data):
        """插入关联数据到指定分表（冲突键取分表主键 id）。"""
        # 列集固定、表名运行期确定，改走 dialect.upsert 生成三库通用幂等语句，
        # 不再硬编码 SQLite 专属语法。
        sql = upsert(
            table_name,
            ['id', 'bk_obj_id', 'bk_inst_id', 'bk_asst_obj_id', 'bk_asst_inst_id',
             'bk_obj_asst_id', 'bk_relation_type_id', 'bk_supplier_account'],
            [':id', ':bk_obj_id', ':bk_inst_id', ':bk_asst_obj_id', ':bk_asst_inst_id',
             ':bk_obj_asst_id', ':bk_relation_type_id', ':bk_supplier_account'],
            conflict='id',
        )
        self.execute_sql(sql, assoc_data)

    def _ensure_all_inst_asst_tables_exist(self):
        """
        确保所有模型的实例关联分表都存在
        包括 cc_ObjDes 中的所有模型 + host 模型
        """
        # 查询所有模型
        models = self.execute_query('migrate/select_all_model_ids.sql')
        model_ids = [m['bk_obj_id'] for m in models]
        
        # 确保包含 host 模型（即使不在 cc_ObjDes 中）
        if 'host' not in model_ids:
            model_ids.append('host')
        
        # 为每个模型创建实例关联分表
        for model_id in model_ids:
            self.create_instance_association_table(model_id)
        
        logger.info(f"创建了 {len(model_ids)} 个实例关联分表")

    def migrate(self):
        """执行完整的迁移"""
        logger.info("开始数据库初始化迁移...")

        # 步骤1: 初始化核心表
        self.init_core_tables()

        # 步骤1.1: 创建 cc_HostBase 和 cc_ModuleHostConfig 表索引
        self.create_hostbase_indexes()
        self.create_module_host_config_indexes()

        # 步骤2: 迁移分类
        self.migrate_classifications()

        # 步骤3: 迁移模型
        self.migrate_models()

        # 步骤3.1: 迁移内置模型（biz/set/module）
        self.migrate_builtin_models()

        # 步骤4: 迁移属性
        self.migrate_attributes()

        # 步骤4.1: 迁移内置模型属性
        self.migrate_builtin_model_attributes()

        # 步骤5: 迁移属性分组
        self.migrate_property_groups()

        # 步骤6: 更新属性分组
        self.update_attributes_group()

        # 步骤7: 创建实例表（跳过内置模型和 host 模型，它们有专用表）
        models = self.execute_query('migrate/select_all_model_ids.sql')
        builtin_model_ids = {m["bk_obj_id"] for m in BUILTIN_MODELS}
        builtin_model_ids.add("host")
        for model in models:
            if model['bk_obj_id'] not in builtin_model_ids:
                self.create_instance_table(model['bk_obj_id'])

        # 步骤7.1: 补齐 host / 通用模型的内置时间属性（创建时间 / 最后修改时间）
        # 放在实例表创建之后，可同时校正历史模型的实例表缺列问题
        self.ensure_builtin_time_attributes()

        # 步骤7.2: 补齐自定义主线实例表的 bk_biz_id / bk_parent_id / default 列
        # （对齐上游每个主线实例表均含 bk_parent_id；历史表补列，新表由 DDL 自带）
        self.ensure_mainline_columns()

        # 步骤7.3: 补齐 cc_ModuleBase.service_category_id 列（存量库升级，幂等）
        # 对齐上游模块实例携带 service_category_id 字段（新建模块弹框「所属服务分类」落库点）
        self.ensure_module_service_category_column()

        # 步骤7.4: 种子化两级内置 Default 服务分类（全局 bk_biz_id=0 / is_built_in=1）
        # 对齐上游 x19.05.16.01/add_default_category.go 的 addDefaultCategory，
        # 使新建模块的「所属服务分类」具备 Default/Default 默认项
        self.ensure_default_service_category()

        # 步骤8: 迁移实例数据
        self.migrate_instances()

        # 步骤9: 迁移关联关系数据
        self.migrate_associations()

        # 步骤9.1: 归一化关联类型方向值域（存量库升级，幂等）
        # lite 早期把 direction 写成 'forward'（不属上游 AssociationDirection 值域），
        # 统一归一为 none / src_to_dest / dest_to_src / bidirectional
        self.normalize_association_directions()

        # 步骤10: 迁移唯一约束数据
        self.migrate_object_unique()

        # 步骤11: 迁移主线拓扑数据（5个核心表）
        self.migrate_mainline_topo()

        # 步骤11.1: 种子化主线拓扑模型关联（cc_ObjAsst.bk_asst_id='bk_mainline'）
        # 使 get_mainline_model_top 完全数据驱动，支持后续 CLI 自定义多模型多层级
        self.migrate_mainline_associations()

        # 步骤11.2: 存量模块回填默认服务分类（Default/Default）
        # 对齐上游 x19.05.16.01/upgrade_service_template.go：迁移期给模块赋默认分类，
        # 保证「每个模块都有服务分类」。仅回填 service_category_id = 0/NULL 的行，幂等。
        self.backfill_module_default_category()

        logger.info("数据库初始化迁移完成!")

    def ensure_mainline_columns(self):
        """补齐自定义主线实例表的 bk_biz_id / bk_parent_id / default 列。

        对齐上游 bk-cmdb：每一个主线实例表（cc_SetBase / cc_ModuleBase /
        cc_ObjectBase_0_pub_<obj>）都带 bk_biz_id（业务归属）与 bk_parent_id
        （主线父实例ID）两列。lite 早期自定义实例表 DDL 缺这两列，此处以
        M5（先探测再 ALTER）方式幂等补列，保证历史数据与新模型一致。
        """
        rows = [t for t in list_table_names()
                if t.startswith('cc_ObjectBase_0_pub_')]
        for tbl in rows:
            cols = {c for c in get_column_names(tbl)}
            for col, ctype in (('bk_biz_id', 'INTEGER DEFAULT 0'),
                               ('bk_parent_id', 'INTEGER DEFAULT 0'),
                               ('default', 'INTEGER DEFAULT 0')):
                if col not in cols:
                    self.execute_sql(
                        f'ALTER TABLE "{tbl}" ADD COLUMN "{col}" {ctype}')
                    logger.info(f"主线补列 {tbl}.{col}")
        logger.info("自定义主线实例表补列完成")

    def normalize_association_directions(self):
        """把 cc_AsstDes.direction 归一到上游合法值域（存量库升级，幂等）。

        上游 metadata.AssociationDirection 只有 4 个取值：
            none / src_to_dest / dest_to_src / bidirectional
        而 lite 早期 migrate 种子写入的是 'forward' —— 既不被上游接口识别，
        也无法表达"无方向 / 双向"语义，导致关联类型的方向数据实际不可用。

        归一规则见 app/definitions.normalize_asst_direction：
          forward → src_to_dest、backward → dest_to_src、both → bidirectional，
          空值 / 无法识别 → src_to_dest（与上游预置类型方向一致）。

        只改写值域外的行；已是合法值的行（含用户自建的 none / bidirectional）
        原样保留，因此可重复执行。
        """
        rows = self.execute_query(
            'SELECT bk_asst_id, direction FROM cc_AsstDes')
        if not rows:
            return

        fixed = []
        for row in rows:
            current = row.get('direction')
            if current in VALID_ASST_DIRECTIONS:
                continue
            target = normalize_asst_direction(current)
            self.execute_sql(
                'UPDATE cc_AsstDes SET direction = :d, last_time = CURRENT_TIMESTAMP '
                'WHERE bk_asst_id = :a',
                {'d': target, 'a': row['bk_asst_id']})
            fixed.append(f"{row['bk_asst_id']}: {current!r} -> {target!r}")

        if fixed:
            logger.info(f"归一化关联类型方向 {len(fixed)} 项: {'; '.join(fixed)}")
        else:
            logger.info("关联类型方向均已在合法值域内，无需归一化")

    def ensure_module_service_category_column(self):
        """为 cc_ModuleBase 补齐 service_category_id / bk_module_type 列（存量库升级，幂等）。

        对齐上游 bk-cmdb 模块实例字段：
          - service_category_id（definitions.go: BKServiceCategoryIDField）：新建模块弹框「所属服务分类」落库点；
          - bk_module_type（definitions.go: BKModuleTypeField）：模块类型枚举（1=普通 / 2=数据库，默认普通）。
        新库由 DDL 自带这两列，此处以先探测再 ALTER 的方式仅对缺失列的存量库补列。
        """
        cols = {c for c in get_column_names('cc_ModuleBase')}
        if 'service_category_id' not in cols:
            self.execute_sql(
                'ALTER TABLE "cc_ModuleBase" ADD COLUMN "service_category_id" INTEGER DEFAULT 0')
            logger.info("模块表补列 cc_ModuleBase.service_category_id")
        if 'bk_module_type' not in cols:
            self.execute_sql(
                'ALTER TABLE "cc_ModuleBase" ADD COLUMN "bk_module_type" VARCHAR DEFAULT \'1\'')
            logger.info("模块表补列 cc_ModuleBase.bk_module_type")

    def backfill_module_default_category(self):
        """存量模块回填内置默认服务分类（Default 二级），幂等。

        对齐上游 x19.05.16.01/upgrade_service_template.go：迁移期把默认分类
        （addDefaultCategory 返回的二级分类 id）赋给模块，保证「每个模块都有
        服务分类」。lite 无服务模板，直接回填 cc_ModuleBase.service_category_id。

        仅处理 service_category_id IS NULL 或 = 0 的行；已显式指定分类的模块不动。
        无内置默认分类时跳过（不阻塞迁移）。
        """
        from app.service.service_category_service import get_default_category_id

        default_id = get_default_category_id('0')
        if not default_id:
            logger.info("跳过模块服务分类回填：未找到内置默认分类")
            return

        result = self.execute_sql(
            'UPDATE cc_ModuleBase SET service_category_id = :cid '
            'WHERE service_category_id IS NULL OR service_category_id = 0',
            {'cid': default_id})
        logger.info("存量模块回填默认服务分类 Default/Default(%s)", default_id)
        return result

    def ensure_default_service_category(self):
        """种子化两级内置 Default 服务分类（幂等，新库 / 存量库通用）。

        对齐上游 bk-cmdb x19.05.16.01/add_default_category.go（addDefaultCategory）：
          一级：name='Default', bk_parent_id=0,   bk_root_id=自身 id,
                bk_biz_id=0（全局，非业务私有）, bk_supplier_account='0', is_built_in=1
          二级：name='Default', bk_parent_id=一级 id, bk_root_id=一级 root_id,
                bk_biz_id=0（全局）, bk_supplier_account='0', is_built_in=1

        作用：新建模块弹框「所属服务分类」具备 Default/Default 默认选项；
        未显式传 service_category_id 的模块创建也回退到该二级分类
        （对齐上游 CreateModule -> GetDefaultServiceCategory）。

        幂等：按 (bk_biz_id=0, name='Default', bk_parent_id) 探测，存在即复用，不重复插入。
        """
        # 建表（幂等，多方言 DDL 由 service_category_service 内部转译）
        from app.service.service_category_service import (
            init_service_category_table, DEFAULT_CATEGORY_NAME)
        init_service_category_table()

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        supplier = '0'

        def _find(parent_id):
            rows = self.execute_query(
                'SELECT id FROM cc_ServiceCategory '
                'WHERE bk_biz_id = 0 AND bk_supplier_account = :s '
                '  AND bk_parent_id = :pid AND name = :name',
                {'s': supplier, 'pid': parent_id, 'name': DEFAULT_CATEGORY_NAME})
            return int(rows[0]['id']) if rows else None

        # 一级 Default
        first_id = _find(0)
        if first_id is None:
            first_id = generate_id(scope='service_category')
            self.execute_sql(
                'migrate/insert_service_category.sql',
                {'id': first_id, 'name': DEFAULT_CATEGORY_NAME,
                 'root': first_id, 'pid': 0, 's': supplier, 't': now})
            logger.info("种子化内置一级服务分类 Default(id=%s)", first_id)

        # 二级 Default（父级 = 一级 Default）
        second_id = _find(first_id)
        if second_id is None:
            second_id = generate_id(scope='service_category')
            self.execute_sql(
                'migrate/insert_service_category.sql',
                {'id': second_id, 'name': DEFAULT_CATEGORY_NAME,
                 'root': first_id, 'pid': first_id, 's': supplier, 't': now})
            logger.info("种子化内置二级服务分类 Default(id=%s)", second_id)

        logger.info("内置默认服务分类就绪：Default/Default = %s/%s", first_id, second_id)

    def migrate_mainline_associations(self):
        """种子化主线拓扑模型关联（cc_ObjAsst.bk_asst_id='bk_mainline'）。

        对齐上游 createMainlineObjectAssociation：内置主线链 biz -> set -> module
        以 cc_ObjAsst 的 bk_mainline 关联行表达（bk_obj_id=子, target_obj_id=父）。
        幂等：依据 bk_obj_asst_id 去重，避免重复迁移覆盖用户后续自定义主线。
        """
        mainline_chain = [
            {
                "bk_obj_id": "set",
                "target_obj_id": "biz",
                "target_obj_name": "业务",
                "bk_obj_asst_id": "set_mainline_biz",
                "bk_obj_asst_name": "属于业务",
                "mapping": "1:n",
            },
            {
                "bk_obj_id": "module",
                "target_obj_id": "set",
                "target_obj_name": "集群",
                "bk_obj_asst_id": "module_mainline_set",
                "bk_obj_asst_name": "属于集群",
                "mapping": "1:n",
            },
        ]
        for idx, m in enumerate(mainline_chain, start=9001):
            exists = self.execute_query(
                "SELECT 1 FROM cc_ObjAsst WHERE bk_obj_asst_id=:aid",
                {"aid": m["bk_obj_asst_id"]})
            if exists:
                continue
            self.execute_sql("""
                INSERT INTO cc_ObjAsst
                (id, bk_obj_id, target_obj_id, target_obj_name, bk_asst_id,
                 bk_obj_asst_id, bk_obj_asst_name, mapping, on_delete,
                 creator, modifier, bk_supplier_account)
                VALUES (:id, :bk_obj_id, :target_obj_id, :target_obj_name, 'bk_mainline',
                        :bk_obj_asst_id, :bk_obj_asst_name, :mapping, 'none',
                        'admin', 'admin', '0')
            """, {
                "id": idx,
                "bk_obj_id": m["bk_obj_id"],
                "target_obj_id": m["target_obj_id"],
                "target_obj_name": m["target_obj_name"],
                "bk_obj_asst_id": m["bk_obj_asst_id"],
                "bk_obj_asst_name": m["bk_obj_asst_name"],
                "mapping": m["mapping"],
            })
        logger.info("主线拓扑模型关联种子化完成")

    def migrate_object_unique(self):
        """迁移唯一约束数据。

        对齐上游内置初始化，按模型真实「名称字段」构造唯一约束：
        - 自定义主线模型（有 bk_inst_name，如 appsys/应用系统）：(bk_parent_id, bk_inst_name) 复合键；
        - 内置主线模型 set/module：使用专属名称字段 (bk_set_name / bk_module_name)，
          同样构成 (bk_parent_id, 名称字段) 复合键（同父节点下名称唯一）；
        - 业务 biz：无父节点，名称字段 bk_biz_name 全局唯一（单键）。

        名称「键」由 model_name_property 按模型解析，避免内置模型因无 bk_inst_name
        属性而建不出规则（这正是此前 set/module 重名能被提交的根因）。
        每轮 migrate 重放，采用 INSERT OR REPLACE + 仅保留本次写入的 ispre=1 规则保证幂等。
        """
        models = self.execute_query('migrate/select_all_model_ids.sql')

        unique_id = 1
        for model in models:
            model_id = model['bk_obj_id']

            # 是否主线模型（用于缺失 bk_parent_id 时的兜底补建）
            is_mainline = bool(self.execute_query(
                "SELECT 1 FROM cc_ObjAsst WHERE bk_asst_id='bk_mainline' AND bk_obj_id=:o",
                {"o": model_id}))

            # 解析名称字段：自定义主线用 bk_inst_name，内置 set/module/biz 用专属名称字段
            inst_name = self.execute_query(
                "SELECT id FROM cc_ObjAttDes WHERE bk_obj_id=:m AND bk_property_id='bk_inst_name'",
                {"m": model_id})
            name_field = model_name_property(model_id, bool(inst_name))
            if not name_field:
                continue
            name_result = self.execute_query(
                "SELECT id FROM cc_ObjAttDes WHERE bk_obj_id=:m AND bk_property_id=:p",
                {"m": model_id, "p": name_field})
            if not name_result:
                continue
            name_id = name_result[0]['id']

            # 是否含 bk_parent_id（set/module/appsys 有，biz 无）→ 复合键或单键
            pid_result = self.execute_query(
                "SELECT id FROM cc_ObjAttDes WHERE bk_obj_id=:m AND bk_property_id='bk_parent_id'",
                {"m": model_id})
            # 主线模型但缺失 bk_parent_id（理论不应发生，兜底对齐上游 createDefaultAttrs）
            if is_mainline and not pid_result:
                self._insert_mainline_parent_attr(model_id)
                pid_result = self.execute_query(
                    "SELECT id FROM cc_ObjAttDes WHERE bk_obj_id=:m AND bk_property_id='bk_parent_id'",
                    {"m": model_id})

            if pid_result:
                pid_id = pid_result[0]['id']
                keys = json.dumps([
                    {"key_kind": "property", "key_id": pid_id},
                    {"key_kind": "property", "key_id": name_id},
                ])
            else:
                # biz：无父节点，名称全局唯一（单键）
                keys = json.dumps([{"key_kind": "property", "key_id": name_id}])
            _id = f"{model_id}_name_unique"

            # 通用 (父,名) / 单键 唯一约束种子（冲突键取主键 id，幂等重放）
            self.execute_sql(
                self.upsert_sql('cc_ObjectUnique',
                               ['_id', 'id', 'bk_obj_id', 'keys', 'ispre',
                                'bk_supplier_account'],
                               conflict='id',
                               literals={'bk_supplier_account': "'0'"}), {
                '_id': _id,
                'id': unique_id,
                'bk_obj_id': model_id,
                'keys': keys,
                'ispre': True
            })
            # 幂等保障：每个模型仅保留一条本次迁移写入的内置唯一约束（ispre=1），
            # 避免 cc_ObjectUnique 以 id 为主键导致 re-migrate 时重复追加；
            # 仅清理 ispre=1（预设）规则，保留用户经模型管理增删的 ispre=0 规则。
            # 旧的残留规则（不同 _id 命名，如 xxx_bk_inst_name）也会被一并清除。
            # 交换机/主机等额外预设规则由循环后的 _migrate_special_unique 重新写入，不会丢失。
            # 必须在循环内按当前模型清理，否则仅末位模型能被去重。
            self.execute_sql(
                "DELETE FROM cc_ObjectUnique WHERE bk_obj_id=:o AND bk_supplier_account='0' "
                "AND ispre=1 AND id != :keep",
                {"o": model_id, "keep": unique_id})
            unique_id += 1

        # 交换机/主机等额外预设唯一约束（与通用 (父,名) 规则并存，循环内去重后会重建）
        self._migrate_special_unique()

    def _insert_mainline_parent_attr(self, model_id):
        """为缺失 bk_parent_id 属性的主线模型补建该属性（isonly=true，系统字段）。

        对齐上游 mainline createDefaultAttrs 写入的 bk_parent_id，作为
        (bk_parent_id, bk_inst_name) 复合唯一约束的键之一。
        """
        row = self.execute_query('migrate/select_max_attribute_id.sql')
        next_id = (row[0]['max_id'] if row and row[0].get('max_id') is not None else 0) + 1
        option = self.process_option('int', None)
        # 主线模型补建 bk_parent_id 属性（复合主键 upsert，bk_supplier_account 固定 '0'）
        self.execute_sql(
            self.upsert_sql('cc_ObjAttDes', self.OBJATTDES_COLUMNS,
                           conflict=self.OBJATTDES_CONFLICT,
                           literals=self.OBJATTDES_LITERALS), {
            '_id': f"{model_id}.bk_parent_id",
            'id': next_id,
            'bk_obj_id': model_id,
            'bk_property_id': 'bk_parent_id',
            'bk_property_name': '父节点ID',
            'bk_property_type': 'int',
            'bk_property_group': 'default',
            'isrequired': True,
            'bk_ispassword': False,
            'bk_ishidden': False,
            'isreadonly': True,
            'isonly': True,
            'bk_isapi': False,
            'bk_issystem': True,
            'option': option,
            'unit': '',
            'placeholder': '',
            'editable': False,
            'ispre': True,
            'bk_property_index': -1,
        })

    def _migrate_special_unique(self):
        """为特定内置模型追加额外的预设唯一约束（与通用 (父,名) 规则并存）。

        交换机：(bk_inst_name, management_ip) 组合唯一；主机：bk_host_outerip 唯一。
        使用固定 _id / id，INSERT OR REPLACE 保证 re-migrate 幂等；不参与
        migrate_object_unique 循环内「按模型同名规则去重」，故不会被清除。
        """
        # 交换机：(bk_inst_name, management_ip) 组合唯一
        inst = self.execute_query(
            "SELECT id FROM cc_ObjAttDes WHERE bk_obj_id='bk_switch' AND bk_property_id='bk_inst_name'")
        mip = self.execute_query(
            "SELECT id FROM cc_ObjAttDes WHERE bk_obj_id='bk_switch' AND bk_property_id='management_ip'")
        if inst and mip:
            combo_keys = json.dumps([
                {"key_kind": "property", "key_id": inst[0]['id']},
                {"key_kind": "property", "key_id": mip[0]['id']},
            ])
            # 交换机 (bk_inst_name, management_ip) 组合唯一（冲突键 id，ispre=1 预设）
            self.execute_sql(
                self.upsert_sql('cc_ObjectUnique',
                               ['_id', 'id', 'bk_obj_id', 'keys', 'ispre',
                                'bk_supplier_account'],
                               conflict='id',
                               literals={'ispre': "'1'", 'bk_supplier_account': "'0'"}),
                {"_id": "bk_switch_bk_inst_name_management_ip", "id": 900001,
                 "bk_obj_id": "bk_switch", "keys": combo_keys})

        # 主机：bk_host_outerip 唯一
        oip = self.execute_query(
            "SELECT id FROM cc_ObjAttDes WHERE bk_obj_id='host' AND bk_property_id='bk_host_outerip'")
        if oip:
            outer_ip_keys = json.dumps(
                [{"key_kind": "property", "key_id": oip[0]['id']}])
            # 主机 bk_host_outerip 唯一（冲突键 id，ispre=1 预设）
            self.execute_sql(
                self.upsert_sql('cc_ObjectUnique',
                               ['_id', 'id', 'bk_obj_id', 'keys', 'ispre',
                                'bk_supplier_account'],
                               conflict='id',
                               literals={'ispre': "'1'", 'bk_supplier_account': "'0'"}),
                {"_id": "host_bk_host_outerip", "id": 900002,
                 "bk_obj_id": "host", "keys": outer_ip_keys})

    # ------------------------------------------------------------------
    # 种子主机挂载（重构：按业务拓扑语义解析，不再硬编码模块 ID）
    # ------------------------------------------------------------------
    def _resolve_set(self, biz_id, set_name, default=None):
        """按 (业务, 集群名[, default]) 解析 bk_set_id。"""
        sql = ("SELECT bk_set_id FROM cc_SetBase "
               "WHERE bk_biz_id=:b AND bk_set_name=:sn AND bk_supplier_account='0'")
        params = {'b': biz_id, 'sn': set_name}
        if default is not None:
            sql += ' AND "default"=:d'
            params['d'] = default
        rows = self.execute_query(sql + " ORDER BY bk_set_id LIMIT 1", params)
        return rows[0]['bk_set_id'] if rows else None

    def _ensure_set(self, biz_id, set_name, default=0):
        """按 (业务, 集群名) 解析 bk_set_id；不存在则用 generate_id 创建（bk_parent_id=biz）。"""
        sid = self._resolve_set(biz_id, set_name, default if default else None)
        if sid is not None:
            return sid
        sid = generate_id()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.execute_sql(
            'INSERT INTO cc_SetBase '
            '(bk_set_id, bk_set_name, bk_parent_id, bk_biz_id, "default", bk_supplier_account, create_time, last_time) '
            'VALUES (:bk_set_id, :bk_set_name, :bk_parent_id, :bk_biz_id, :default, :bk_supplier_account, :create_time, :last_time)',
            {'bk_set_id': sid, 'bk_set_name': set_name, 'bk_parent_id': biz_id,
             'bk_biz_id': biz_id, 'default': default, 'bk_supplier_account': '0',
             'create_time': now, 'last_time': now})
        logger.info(f"为主机挂载补全创建集群 biz{biz_id}/{set_name} (set{sid})")
        return sid

    def _resolve_module(self, biz_id, set_name, module_name):
        """按 (业务, 集群名, 模块名) 解析 (bk_module_id, bk_set_id)。"""
        rows = self.execute_query(
            "SELECT m.bk_module_id, m.bk_set_id FROM cc_ModuleBase m "
            "JOIN cc_SetBase s ON s.bk_set_id=m.bk_set_id AND s.bk_supplier_account=m.bk_supplier_account "
            "WHERE m.bk_biz_id=:b AND m.bk_module_name=:mn AND s.bk_set_name=:sn "
            "AND m.bk_supplier_account='0' AND s.bk_supplier_account='0' "
            "ORDER BY m.bk_module_id LIMIT 1",
            {'b': biz_id, 'mn': module_name, 'sn': set_name})
        return (rows[0]['bk_module_id'], rows[0]['bk_set_id']) if rows else None

    def _ensure_module(self, biz_id, set_name, module_name, default=0):
        """按 (业务, 集群名, 模块名) 解析 (bk_module_id, bk_set_id)；不存在则补全集群与模块。"""
        res = self._resolve_module(biz_id, set_name, module_name)
        if res:
            return res
        sid = self._ensure_set(biz_id, set_name, 1 if set_name == '空闲机池' else 0)
        mid = generate_id()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.execute_sql(
            'INSERT INTO cc_ModuleBase '
            '(bk_module_id, bk_module_name, bk_parent_id, bk_set_id, bk_biz_id, "default", bk_supplier_account, create_time, last_time) '
            'VALUES (:bk_module_id, :bk_module_name, :bk_parent_id, :bk_set_id, :bk_biz_id, :default, :bk_supplier_account, :create_time, :last_time)',
            {'bk_module_id': mid, 'bk_module_name': module_name, 'bk_parent_id': sid,
             'bk_set_id': sid, 'bk_biz_id': biz_id, 'default': default,
             'bk_supplier_account': '0', 'create_time': now, 'last_time': now})
        logger.info(f"为主机挂载补全创建模块 biz{biz_id}/{set_name}/{module_name} (module{mid})")
        return (mid, sid)

    def seed_host_bindings(self):
        """幂等重建 21 台种子主机到业务拓扑目标模块的挂载关系。

        对齐真实 CMDB 主机归属语义：
        - 挂载目标以 (业务, 集群名, 模块名) 表达，运行时解析实际 bk_module_id/bk_set_id，
          不再硬编码 ID，避免模块被 generate_id 重新生成后 ID 漂移导致悬空绑定。
        - 目标模块/集群缺失时自动补全创建（generate_id 发号），保证挂载总能落库。
        - 每次重放先清除这些种子主机既有绑定再写入，re-migrate 与修复脚本均幂等。
        """
        host_ids = [s['bk_host_id'] for s in HOST_BINDING_SPEC]
        ph = ','.join(str(h) for h in host_ids)
        self.execute_sql(
            f"DELETE FROM cc_ModuleHostConfig WHERE bk_host_id IN ({ph}) "
            f"AND bk_supplier_account='0'")
        bound = 0
        for spec in HOST_BINDING_SPEC:
            mid, sid = self._ensure_module(
                spec['bk_biz_id'], spec['bk_set_name'], spec['bk_module_name'])
            self.execute_sql(
                "INSERT INTO cc_ModuleHostConfig "
                "(bk_biz_id, bk_host_id, bk_module_id, bk_set_id, bk_supplier_account) "
                "VALUES (:bk_biz_id, :bk_host_id, :bk_module_id, :bk_set_id, :bk_supplier_account)",
                {'bk_biz_id': spec['bk_biz_id'], 'bk_host_id': spec['bk_host_id'],
                 'bk_module_id': mid, 'bk_set_id': sid, 'bk_supplier_account': '0'})
            bound += 1
        logger.info(f"种子主机挂载关系已重建：{bound} 条（按业务拓扑语义解析，无悬空）")

    def migrate_mainline_topo(self):
        """
        迁移主线拓扑数据
        
        根据原项目分析文档，初始化主线拓扑的核心实例数据：
        - cc_ApplicationBase: 业务实例（含资源池/空闲机池）
        - cc_SetBase: 集群实例
        - cc_ModuleBase: 模块实例
        - cc_HostBase: 主机实例
        - cc_ModuleHostConfig: 主机-模块挂载关系
        
        bk_supplier_account 统一使用 '0'
        """
        logger.info("开始迁移主线拓扑数据...")
        
        # 1. 创建默认业务（资源池/空闲机池）
        # 原项目 default=1 表示内置资源池业务
        default_biz = {
            "bk_biz_id": 1,
            "bk_biz_name": "资源池",
            "default": 1,
            "bk_supplier_account": "0"
        }
        
        # 资源池业务（冲突键 bk_biz_id，幂等重放）
        self.execute_sql(
            self.upsert_sql('cc_ApplicationBase',
                           ['bk_biz_id', 'bk_biz_name', 'default',
                            'bk_supplier_account'],
                           conflict='bk_biz_id'),
            default_biz)
        
        # 创建示例业务
        demo_biz_list = [
            {"bk_biz_id": 2, "bk_biz_name": "蓝鲸平台", "default": 0, "bk_supplier_account": "0"},
            {"bk_biz_id": 3, "bk_biz_name": "正式环境", "default": 0, "bk_supplier_account": "0"},
            {"bk_biz_id": 4, "bk_biz_name": "测试环境", "default": 0, "bk_supplier_account": "0"},
            {"bk_biz_id": 5, "bk_biz_name": "预发布环境", "default": 0, "bk_supplier_account": "0"},
        ]
        
        # 示例业务：冲突键 bk_biz_id，语句在循环外生成一次（内容与行数据无关）
        demo_biz_upsert = self.upsert_sql(
            'cc_ApplicationBase',
            ['_id', 'bk_biz_id', 'bk_biz_name', 'default', 'bk_supplier_account'],
            conflict='bk_biz_id',
        )
        for biz in demo_biz_list:
            self.execute_sql(
                demo_biz_upsert,
                biz | {"_id": f"biz_{biz['bk_biz_id']}"})
        
        logger.info(f"创建了 {1 + len(demo_biz_list)} 个业务实例")
        
        # 2. 创建集群（空闲机池集群 + 示例集群）
        # 原项目规则：
        # - 每个业务都有一个空闲机池集群（default=1）
        # - 集群的 bk_parent_id 指向业务的 bk_biz_id
        # - 空闲机池的 default=1（表示内置集群）
        #
        # 置顶规则（与查询排序保持一致）：
        # 因空闲机池的 bk_parent_id 指向 biz，而在含自定义主线层（appsys 等）的业务里
        # set 的父模型被识别为 appsys，空闲机池会作为孤儿挂到业务节点子列表末尾。
        # 查询侧 get_mainline_instance_topo() 会将其稳定置顶到业务节点首位
        # （root.children.sort(key=lambda n: 0 if n.object_id=='set' and n.default==1 else 1)）。
        # 此处插入顺序将空闲机池集群排在最前，且必须保持 default=1、bk_parent_id=bk_biz_id，
        # 以保证迁移初始化后的拓扑树中空闲机池始终位于业务首位。
        set_list = [
            # 空闲机池集群（属于资源池业务 bk_biz_id=1）
            {"bk_set_id": 1, "bk_set_name": "空闲机池", "bk_parent_id": 1, "bk_biz_id": 1, "default": 1, "bk_supplier_account": "0"},
            # 空闲机池集群（属于蓝鲸平台业务 bk_biz_id=2）
            {"bk_set_id": 2, "bk_set_name": "空闲机池", "bk_parent_id": 2, "bk_biz_id": 2, "default": 1, "bk_supplier_account": "0"},
            # 空闲机池集群（属于正式环境业务 bk_biz_id=3）
            {"bk_set_id": 3, "bk_set_name": "空闲机池", "bk_parent_id": 3, "bk_biz_id": 3, "default": 1, "bk_supplier_account": "0"},
            # 空闲机池集群（属于测试环境业务 bk_biz_id=4）
            {"bk_set_id": 4, "bk_set_name": "空闲机池", "bk_parent_id": 4, "bk_biz_id": 4, "default": 1, "bk_supplier_account": "0"},
            # 空闲机池集群（属于预发布环境业务 bk_biz_id=5）
            {"bk_set_id": 5, "bk_set_name": "空闲机池", "bk_parent_id": 5, "bk_biz_id": 5, "default": 1, "bk_supplier_account": "0"},
            # 蓝鲸平台业务下的普通集群
            {"bk_set_id": 10, "bk_set_name": "广州一区", "bk_parent_id": 2, "bk_biz_id": 2, "default": 0, "bk_supplier_account": "0"},
            {"bk_set_id": 11, "bk_set_name": "广州二区", "bk_parent_id": 2, "bk_biz_id": 2, "default": 0, "bk_supplier_account": "0"},
            # 正式环境业务下的普通集群
            {"bk_set_id": 20, "bk_set_name": "生产集群", "bk_parent_id": 3, "bk_biz_id": 3, "default": 0, "bk_supplier_account": "0"},
            # 测试环境业务下的普通集群
            {"bk_set_id": 30, "bk_set_name": "测试集群", "bk_parent_id": 4, "bk_biz_id": 4, "default": 0, "bk_supplier_account": "0"},
        ]
        
        # 集群：冲突键 bk_set_id，语句在循环外生成一次（内容与行数据无关）
        set_upsert = self.upsert_sql(
            'cc_SetBase',
            ['_id', 'bk_set_id', 'bk_set_name', 'bk_parent_id', 'bk_biz_id',
             'default', 'bk_supplier_account'],
            conflict='bk_set_id',
        )
        for s in set_list:
            self.execute_sql(
                set_upsert,
                s | {"_id": f"set_{s['bk_set_id']}"})
        
        logger.info(f"创建了 {len(set_list)} 个集群实例（含空闲机池）")
        
        # 3. 创建模块
        # 原项目规则：
        # - 模块的 bk_parent_id 指向集群的 bk_set_id
        # - default 字段值：
        #   - 0: 普通模块
        #   - 1: 空闲机模块
        #   - 2: 故障机模块
        #   - 3: 待回收模块
        # - 每个空闲机池集群（default=1）都包含空闲机、故障机、待回收三个模块
        module_list = [
            # 资源池空闲机池集群的模块
            {"bk_module_id": 1, "bk_module_name": "空闲机", "bk_parent_id": 1, "bk_set_id": 1, "bk_biz_id": 1, "default": 1, "bk_supplier_account": "0"},
            {"bk_module_id": 2, "bk_module_name": "故障机", "bk_parent_id": 1, "bk_set_id": 1, "bk_biz_id": 1, "default": 2, "bk_supplier_account": "0"},
            {"bk_module_id": 3, "bk_module_name": "待回收", "bk_parent_id": 1, "bk_set_id": 1, "bk_biz_id": 1, "default": 3, "bk_supplier_account": "0"},
            # 蓝鲸平台空闲机池集群的模块
            {"bk_module_id": 4, "bk_module_name": "空闲机", "bk_parent_id": 2, "bk_set_id": 2, "bk_biz_id": 2, "default": 1, "bk_supplier_account": "0"},
            {"bk_module_id": 5, "bk_module_name": "故障机", "bk_parent_id": 2, "bk_set_id": 2, "bk_biz_id": 2, "default": 2, "bk_supplier_account": "0"},
            {"bk_module_id": 6, "bk_module_name": "待回收", "bk_parent_id": 2, "bk_set_id": 2, "bk_biz_id": 2, "default": 3, "bk_supplier_account": "0"},
            # 正式环境空闲机池集群的模块
            {"bk_module_id": 7, "bk_module_name": "空闲机", "bk_parent_id": 3, "bk_set_id": 3, "bk_biz_id": 3, "default": 1, "bk_supplier_account": "0"},
            {"bk_module_id": 8, "bk_module_name": "故障机", "bk_parent_id": 3, "bk_set_id": 3, "bk_biz_id": 3, "default": 2, "bk_supplier_account": "0"},
            {"bk_module_id": 9, "bk_module_name": "待回收", "bk_parent_id": 3, "bk_set_id": 3, "bk_biz_id": 3, "default": 3, "bk_supplier_account": "0"},
            # 测试环境空闲机池集群的模块
            {"bk_module_id": 10, "bk_module_name": "空闲机", "bk_parent_id": 4, "bk_set_id": 4, "bk_biz_id": 4, "default": 1, "bk_supplier_account": "0"},
            {"bk_module_id": 11, "bk_module_name": "故障机", "bk_parent_id": 4, "bk_set_id": 4, "bk_biz_id": 4, "default": 2, "bk_supplier_account": "0"},
            {"bk_module_id": 12, "bk_module_name": "待回收", "bk_parent_id": 4, "bk_set_id": 4, "bk_biz_id": 4, "default": 3, "bk_supplier_account": "0"},
            # 预发布环境空闲机池集群的模块
            {"bk_module_id": 13, "bk_module_name": "空闲机", "bk_parent_id": 5, "bk_set_id": 5, "bk_biz_id": 5, "default": 1, "bk_supplier_account": "0"},
            {"bk_module_id": 14, "bk_module_name": "故障机", "bk_parent_id": 5, "bk_set_id": 5, "bk_biz_id": 5, "default": 2, "bk_supplier_account": "0"},
            {"bk_module_id": 15, "bk_module_name": "待回收", "bk_parent_id": 5, "bk_set_id": 5, "bk_biz_id": 5, "default": 3, "bk_supplier_account": "0"},
            # 广州一区下的普通模块
            {"bk_module_id": 100, "bk_module_name": "web", "bk_parent_id": 10, "bk_set_id": 10, "bk_biz_id": 2, "default": 0, "bk_supplier_account": "0"},
            {"bk_module_id": 101, "bk_module_name": "api", "bk_parent_id": 10, "bk_set_id": 10, "bk_biz_id": 2, "default": 0, "bk_supplier_account": "0"},
            # 广州二区下的普通模块
            {"bk_module_id": 110, "bk_module_name": "db", "bk_parent_id": 11, "bk_set_id": 11, "bk_biz_id": 2, "default": 0, "bk_supplier_account": "0"},
            # 生产集群下的普通模块
            {"bk_module_id": 200, "bk_module_name": "app", "bk_parent_id": 20, "bk_set_id": 20, "bk_biz_id": 3, "default": 0, "bk_supplier_account": "0"},
            # 测试集群下的普通模块
            {"bk_module_id": 300, "bk_module_name": "test", "bk_parent_id": 30, "bk_set_id": 30, "bk_biz_id": 4, "default": 0, "bk_supplier_account": "0"},
        ]
        
        # 模块：冲突键 bk_module_id，语句在循环外生成一次（内容与行数据无关）
        module_upsert = self.upsert_sql(
            'cc_ModuleBase',
            ['_id', 'bk_module_id', 'bk_module_name', 'bk_parent_id', 'bk_set_id',
             'bk_biz_id', 'default', 'bk_supplier_account'],
            conflict='bk_module_id',
        )
        for m in module_list:
            self.execute_sql(
                module_upsert,
                m | {"_id": f"module_{m['bk_module_id']}"})
        
        logger.info(f"创建了 {len(module_list)} 个模块实例")
        
        # 4. 创建主机（共21条，用于开发测试分页）
        host_list = [
            {"bk_host_id": 1, "bk_host_name": "web-server-01", "bk_host_innerip": "192.168.1.1", "bk_host_outerip": "10.0.1.1", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "admin", "bk_bak_operator": "backup_admin", "bk_asset_id": "ASSET-001", "bk_sn": "SN-2024-001",
             "bk_comment": "Web服务器", "bk_service_term": 3, "bk_sla": "2", "bk_state_name": "CN", "bk_province_name": "440000", "bk_isp_name": "1",
             "bk_os_type": "1", "bk_os_name": "CentOS", "bk_os_version": "7.9", "bk_os_bit": "64位",
             "bk_cpu": 8, "bk_cpu_mhz": 2400000, "bk_cpu_module": "Intel Xeon E5-2680", "bk_mem": 16384, "bk_disk": 500,
             "bk_mac": "00:11:22:33:44:01", "bk_outer_mac": "00:11:22:33:44:02", "import_from": "2"},
            {"bk_host_id": 2, "bk_host_name": "web-server-02", "bk_host_innerip": "192.168.1.2", "bk_host_outerip": "10.0.1.2", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "admin", "bk_bak_operator": "backup_admin", "bk_asset_id": "ASSET-002", "bk_sn": "SN-2024-002",
             "bk_comment": "Web服务器", "bk_service_term": 3, "bk_sla": "2", "bk_state_name": "CN", "bk_province_name": "440000", "bk_isp_name": "1",
             "bk_os_type": "1", "bk_os_name": "CentOS", "bk_os_version": "7.9", "bk_os_bit": "64位",
             "bk_cpu": 8, "bk_cpu_mhz": 2400000, "bk_cpu_module": "Intel Xeon E5-2680", "bk_mem": 16384, "bk_disk": 500,
             "bk_mac": "00:11:22:33:44:03", "bk_outer_mac": "00:11:22:33:44:04", "import_from": "2"},
            {"bk_host_id": 3, "bk_host_name": "api-server-01", "bk_host_innerip": "192.168.1.3", "bk_host_outerip": "", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "api_admin", "bk_bak_operator": "api_backup", "bk_asset_id": "ASSET-003", "bk_sn": "SN-2024-003",
             "bk_comment": "API服务器", "bk_service_term": 3, "bk_sla": "2", "bk_state_name": "CN", "bk_province_name": "310000", "bk_isp_name": "0",
             "bk_os_type": "1", "bk_os_name": "Ubuntu", "bk_os_version": "20.04", "bk_os_bit": "64位",
             "bk_cpu": 8, "bk_cpu_mhz": 2400000, "bk_cpu_module": "Intel Xeon E5-2670", "bk_mem": 16384, "bk_disk": 300,
             "bk_mac": "00:11:22:33:44:05", "bk_outer_mac": "", "import_from": "2"},
            {"bk_host_id": 4, "bk_host_name": "db-server-01", "bk_host_innerip": "192.168.1.4", "bk_host_outerip": "10.0.1.4", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "dba_admin", "bk_bak_operator": "dba_backup", "bk_asset_id": "ASSET-004", "bk_sn": "SN-2024-004",
             "bk_comment": "数据库服务器", "bk_service_term": 5, "bk_sla": "1", "bk_state_name": "CN", "bk_province_name": "310000", "bk_isp_name": "2",
             "bk_os_type": "1", "bk_os_name": "Ubuntu", "bk_os_version": "22.04", "bk_os_bit": "64位",
             "bk_cpu": 16, "bk_cpu_mhz": 2600000, "bk_cpu_module": "Intel Xeon Gold 6248", "bk_mem": 32768, "bk_disk": 1000,
             "bk_mac": "00:11:22:33:44:06", "bk_outer_mac": "00:11:22:33:44:07", "import_from": "3"},
            {"bk_host_id": 5, "bk_host_name": "app-server-01", "bk_host_innerip": "192.168.1.5", "bk_host_outerip": "", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "app_admin", "bk_bak_operator": "app_backup", "bk_asset_id": "ASSET-005", "bk_sn": "SN-2024-005",
             "bk_comment": "应用服务器", "bk_service_term": 3, "bk_sla": "3", "bk_state_name": "CN", "bk_province_name": "330000", "bk_isp_name": "1",
             "bk_os_type": "1", "bk_os_name": "CentOS", "bk_os_version": "8.0", "bk_os_bit": "64位",
             "bk_cpu": 4, "bk_cpu_mhz": 2200000, "bk_cpu_module": "Intel Xeon E3-1270", "bk_mem": 8192, "bk_disk": 200,
             "bk_mac": "00:11:22:33:44:08", "bk_outer_mac": "", "import_from": "2"},
            {"bk_host_id": 6, "bk_host_name": "app-server-02", "bk_host_innerip": "192.168.1.6", "bk_host_outerip": "10.0.1.6", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "app_admin", "bk_bak_operator": "app_backup", "bk_asset_id": "ASSET-006", "bk_sn": "SN-2024-006",
             "bk_comment": "应用服务器", "bk_service_term": 3, "bk_sla": "3", "bk_state_name": "CN", "bk_province_name": "330000", "bk_isp_name": "1",
             "bk_os_type": "1", "bk_os_name": "CentOS", "bk_os_version": "8.0", "bk_os_bit": "64位",
             "bk_cpu": 4, "bk_cpu_mhz": 2200000, "bk_cpu_module": "Intel Xeon E3-1270", "bk_mem": 8192, "bk_disk": 200,
             "bk_mac": "00:11:22:33:44:09", "bk_outer_mac": "00:11:22:33:44:10", "import_from": "2"},
            {"bk_host_id": 7, "bk_host_name": "job-server-01", "bk_host_innerip": "192.168.1.7", "bk_host_outerip": "", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "job_admin", "bk_bak_operator": "job_backup", "bk_asset_id": "ASSET-007", "bk_sn": "SN-2024-007",
             "bk_comment": "作业服务器", "bk_service_term": 5, "bk_sla": "1", "bk_state_name": "CN", "bk_province_name": "320000", "bk_isp_name": "1",
             "bk_os_type": "1", "bk_os_name": "CentOS", "bk_os_version": "7.9", "bk_os_bit": "64位",
             "bk_cpu": 16, "bk_cpu_mhz": 2600000, "bk_cpu_module": "Intel Xeon Gold 5218", "bk_mem": 32768, "bk_disk": 500,
             "bk_mac": "00:11:22:33:44:11", "bk_outer_mac": "", "import_from": "3"},
            {"bk_host_id": 8, "bk_host_name": "idle-host-01", "bk_host_innerip": "192.168.1.8", "bk_host_outerip": "10.0.1.8", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "admin", "bk_bak_operator": "backup_admin", "bk_asset_id": "ASSET-008", "bk_sn": "SN-2024-008",
             "bk_comment": "空闲主机", "bk_service_term": 3, "bk_sla": "3", "bk_state_name": "CN", "bk_province_name": "110000", "bk_isp_name": "0",
             "bk_os_type": "1", "bk_os_name": "CentOS", "bk_os_version": "7.9", "bk_os_bit": "64位",
             "bk_cpu": 4, "bk_cpu_mhz": 2200000, "bk_cpu_module": "Intel Xeon E3-1240", "bk_mem": 8192, "bk_disk": 200,
             "bk_mac": "00:11:22:33:44:12", "bk_outer_mac": "00:11:22:33:44:13", "import_from": "1"},
            # 新增主机 9-21 用于分页测试
            {"bk_host_id": 9, "bk_host_name": "web-server-03", "bk_host_innerip": "192.168.1.9", "bk_host_outerip": "10.0.1.9", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "admin", "bk_bak_operator": "backup_admin", "bk_asset_id": "ASSET-009", "bk_sn": "SN-2024-009",
             "bk_comment": "Web服务器", "bk_service_term": 3, "bk_sla": "2", "bk_state_name": "CN", "bk_province_name": "440000", "bk_isp_name": "1",
             "bk_os_type": "1", "bk_os_name": "CentOS", "bk_os_version": "7.9", "bk_os_bit": "64位",
             "bk_cpu": 8, "bk_cpu_mhz": 2400000, "bk_cpu_module": "Intel Xeon E5-2680", "bk_mem": 16384, "bk_disk": 500,
             "bk_mac": "00:11:22:33:44:14", "bk_outer_mac": "00:11:22:33:44:15", "import_from": "2"},
            {"bk_host_id": 10, "bk_host_name": "web-server-04", "bk_host_innerip": "192.168.1.10", "bk_host_outerip": "10.0.1.10", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "admin", "bk_bak_operator": "backup_admin", "bk_asset_id": "ASSET-010", "bk_sn": "SN-2024-010",
             "bk_comment": "Web服务器", "bk_service_term": 3, "bk_sla": "2", "bk_state_name": "CN", "bk_province_name": "440000", "bk_isp_name": "1",
             "bk_os_type": "1", "bk_os_name": "CentOS", "bk_os_version": "7.9", "bk_os_bit": "64位",
             "bk_cpu": 8, "bk_cpu_mhz": 2400000, "bk_cpu_module": "Intel Xeon E5-2680", "bk_mem": 16384, "bk_disk": 500,
             "bk_mac": "00:11:22:33:44:16", "bk_outer_mac": "00:11:22:33:44:17", "import_from": "2"},
            {"bk_host_id": 11, "bk_host_name": "api-server-02", "bk_host_innerip": "192.168.1.11", "bk_host_outerip": "", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "api_admin", "bk_bak_operator": "api_backup", "bk_asset_id": "ASSET-011", "bk_sn": "SN-2024-011",
             "bk_comment": "API服务器", "bk_service_term": 3, "bk_sla": "2", "bk_state_name": "CN", "bk_province_name": "310000", "bk_isp_name": "0",
             "bk_os_type": "1", "bk_os_name": "Ubuntu", "bk_os_version": "20.04", "bk_os_bit": "64位",
             "bk_cpu": 8, "bk_cpu_mhz": 2400000, "bk_cpu_module": "Intel Xeon E5-2670", "bk_mem": 16384, "bk_disk": 300,
             "bk_mac": "00:11:22:33:44:18", "bk_outer_mac": "", "import_from": "2"},
            {"bk_host_id": 12, "bk_host_name": "api-server-03", "bk_host_innerip": "192.168.1.12", "bk_host_outerip": "", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "api_admin", "bk_bak_operator": "api_backup", "bk_asset_id": "ASSET-012", "bk_sn": "SN-2024-012",
             "bk_comment": "API服务器", "bk_service_term": 3, "bk_sla": "2", "bk_state_name": "CN", "bk_province_name": "310000", "bk_isp_name": "0",
             "bk_os_type": "1", "bk_os_name": "Ubuntu", "bk_os_version": "20.04", "bk_os_bit": "64位",
             "bk_cpu": 8, "bk_cpu_mhz": 2400000, "bk_cpu_module": "Intel Xeon E5-2670", "bk_mem": 16384, "bk_disk": 300,
             "bk_mac": "00:11:22:33:44:19", "bk_outer_mac": "", "import_from": "2"},
            {"bk_host_id": 13, "bk_host_name": "db-server-02", "bk_host_innerip": "192.168.1.13", "bk_host_outerip": "10.0.1.13", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "dba_admin", "bk_bak_operator": "dba_backup", "bk_asset_id": "ASSET-013", "bk_sn": "SN-2024-013",
             "bk_comment": "数据库服务器", "bk_service_term": 5, "bk_sla": "1", "bk_state_name": "CN", "bk_province_name": "310000", "bk_isp_name": "2",
             "bk_os_type": "1", "bk_os_name": "Ubuntu", "bk_os_version": "22.04", "bk_os_bit": "64位",
             "bk_cpu": 16, "bk_cpu_mhz": 2600000, "bk_cpu_module": "Intel Xeon Gold 6248", "bk_mem": 32768, "bk_disk": 1000,
             "bk_mac": "00:11:22:33:44:20", "bk_outer_mac": "00:11:22:33:44:21", "import_from": "3"},
            {"bk_host_id": 14, "bk_host_name": "db-server-03", "bk_host_innerip": "192.168.1.14", "bk_host_outerip": "10.0.1.14", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "dba_admin", "bk_bak_operator": "dba_backup", "bk_asset_id": "ASSET-014", "bk_sn": "SN-2024-014",
             "bk_comment": "数据库服务器", "bk_service_term": 5, "bk_sla": "1", "bk_state_name": "CN", "bk_province_name": "310000", "bk_isp_name": "2",
             "bk_os_type": "1", "bk_os_name": "Ubuntu", "bk_os_version": "22.04", "bk_os_bit": "64位",
             "bk_cpu": 16, "bk_cpu_mhz": 2600000, "bk_cpu_module": "Intel Xeon Gold 6248", "bk_mem": 32768, "bk_disk": 1000,
             "bk_mac": "00:11:22:33:44:22", "bk_outer_mac": "00:11:22:33:44:23", "import_from": "3"},
            {"bk_host_id": 15, "bk_host_name": "cache-server-01", "bk_host_innerip": "192.168.1.15", "bk_host_outerip": "", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "cache_admin", "bk_bak_operator": "cache_backup", "bk_asset_id": "ASSET-015", "bk_sn": "SN-2024-015",
             "bk_comment": "缓存服务器", "bk_service_term": 3, "bk_sla": "2", "bk_state_name": "CN", "bk_province_name": "320000", "bk_isp_name": "1",
             "bk_os_type": "1", "bk_os_name": "CentOS", "bk_os_version": "7.9", "bk_os_bit": "64位",
             "bk_cpu": 8, "bk_cpu_mhz": 2400000, "bk_cpu_module": "Intel Xeon E5-2680", "bk_mem": 32768, "bk_disk": 200,
             "bk_mac": "00:11:22:33:44:24", "bk_outer_mac": "", "import_from": "2"},
            {"bk_host_id": 16, "bk_host_name": "cache-server-02", "bk_host_innerip": "192.168.1.16", "bk_host_outerip": "", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "cache_admin", "bk_bak_operator": "cache_backup", "bk_asset_id": "ASSET-016", "bk_sn": "SN-2024-016",
             "bk_comment": "缓存服务器", "bk_service_term": 3, "bk_sla": "2", "bk_state_name": "CN", "bk_province_name": "320000", "bk_isp_name": "1",
             "bk_os_type": "1", "bk_os_name": "CentOS", "bk_os_version": "7.9", "bk_os_bit": "64位",
             "bk_cpu": 8, "bk_cpu_mhz": 2400000, "bk_cpu_module": "Intel Xeon E5-2680", "bk_mem": 32768, "bk_disk": 200,
             "bk_mac": "00:11:22:33:44:25", "bk_outer_mac": "", "import_from": "2"},
            {"bk_host_id": 17, "bk_host_name": "mq-server-01", "bk_host_innerip": "192.168.1.17", "bk_host_outerip": "", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "mq_admin", "bk_bak_operator": "mq_backup", "bk_asset_id": "ASSET-017", "bk_sn": "SN-2024-017",
             "bk_comment": "消息队列服务器", "bk_service_term": 5, "bk_sla": "1", "bk_state_name": "CN", "bk_province_name": "330000", "bk_isp_name": "1",
             "bk_os_type": "1", "bk_os_name": "CentOS", "bk_os_version": "7.9", "bk_os_bit": "64位",
             "bk_cpu": 8, "bk_cpu_mhz": 2400000, "bk_cpu_module": "Intel Xeon E5-2680", "bk_mem": 16384, "bk_disk": 500,
             "bk_mac": "00:11:22:33:44:26", "bk_outer_mac": "", "import_from": "2"},
            {"bk_host_id": 18, "bk_host_name": "mq-server-02", "bk_host_innerip": "192.168.1.18", "bk_host_outerip": "", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "mq_admin", "bk_bak_operator": "mq_backup", "bk_asset_id": "ASSET-018", "bk_sn": "SN-2024-018",
             "bk_comment": "消息队列服务器", "bk_service_term": 5, "bk_sla": "1", "bk_state_name": "CN", "bk_province_name": "330000", "bk_isp_name": "1",
             "bk_os_type": "1", "bk_os_name": "CentOS", "bk_os_version": "7.9", "bk_os_bit": "64位",
             "bk_cpu": 8, "bk_cpu_mhz": 2400000, "bk_cpu_module": "Intel Xeon E5-2680", "bk_mem": 16384, "bk_disk": 500,
             "bk_mac": "00:11:22:33:44:27", "bk_outer_mac": "", "import_from": "2"},
            {"bk_host_id": 19, "bk_host_name": "log-server-01", "bk_host_innerip": "192.168.1.19", "bk_host_outerip": "10.0.1.19", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "log_admin", "bk_bak_operator": "log_backup", "bk_asset_id": "ASSET-019", "bk_sn": "SN-2024-019",
             "bk_comment": "日志服务器", "bk_service_term": 5, "bk_sla": "2", "bk_state_name": "CN", "bk_province_name": "110000", "bk_isp_name": "0",
             "bk_os_type": "1", "bk_os_name": "CentOS", "bk_os_version": "7.9", "bk_os_bit": "64位",
             "bk_cpu": 16, "bk_cpu_mhz": 2600000, "bk_cpu_module": "Intel Xeon Gold 5218", "bk_mem": 65536, "bk_disk": 2000,
             "bk_mac": "00:11:22:33:44:28", "bk_outer_mac": "00:11:22:33:44:29", "import_from": "2"},
            {"bk_host_id": 20, "bk_host_name": "monitor-server-01", "bk_host_innerip": "192.168.1.20", "bk_host_outerip": "10.0.1.20", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "monitor_admin", "bk_bak_operator": "monitor_backup", "bk_asset_id": "ASSET-020", "bk_sn": "SN-2024-020",
             "bk_comment": "监控服务器", "bk_service_term": 5, "bk_sla": "1", "bk_state_name": "CN", "bk_province_name": "110000", "bk_isp_name": "0",
             "bk_os_type": "1", "bk_os_name": "CentOS", "bk_os_version": "7.9", "bk_os_bit": "64位",
             "bk_cpu": 8, "bk_cpu_mhz": 2400000, "bk_cpu_module": "Intel Xeon E5-2680", "bk_mem": 16384, "bk_disk": 500,
             "bk_mac": "00:11:22:33:44:30", "bk_outer_mac": "00:11:22:33:44:31", "import_from": "2"},
            {"bk_host_id": 21, "bk_host_name": "backup-server-01", "bk_host_innerip": "192.168.1.21", "bk_host_outerip": "", "bk_cloud_id": 0, "bk_supplier_account": "0",
             "operator": "backup_admin", "bk_bak_operator": "backup_admin", "bk_asset_id": "ASSET-021", "bk_sn": "SN-2024-021",
             "bk_comment": "备份服务器", "bk_service_term": 5, "bk_sla": "3", "bk_state_name": "CN", "bk_province_name": "440000", "bk_isp_name": "1",
             "bk_os_type": "1", "bk_os_name": "CentOS", "bk_os_version": "7.9", "bk_os_bit": "64位",
             "bk_cpu": 8, "bk_cpu_mhz": 2400000, "bk_cpu_module": "Intel Xeon E5-2680", "bk_mem": 16384, "bk_disk": 4000,
             "bk_mac": "00:11:22:33:44:32", "bk_outer_mac": "", "import_from": "2"},
        ]
        
        # 种子主机：冲突键 bk_host_id，语句在循环外生成一次（内容与行数据无关）
        host_upsert = self.upsert_sql(
            'cc_HostBase',
            ['_id', 'bk_host_id', 'bk_host_name', 'bk_host_innerip', 'bk_host_outerip',
             'bk_host_inneripv6', 'bk_host_outeripv6', 'bk_cloud_id', 'bk_cloud_inst_id',
             'bk_agent_id', 'bk_supplier_account', 'operator', 'bk_bak_operator',
             'bk_asset_id', 'bk_sn', 'bk_comment', 'bk_service_term', 'bk_sla',
             'bk_state_name', 'bk_province_name', 'bk_isp_name', 'bk_os_type', 'bk_os_name',
             'bk_os_version', 'bk_os_bit', 'bk_cpu', 'bk_cpu_mhz', 'bk_cpu_module',
             'bk_mem', 'bk_disk', 'bk_mac', 'bk_outer_mac', 'import_from'],
            conflict='bk_host_id',
        )
        for h in host_list:
            self.execute_sql(
                host_upsert,
                h | {"_id": f"host_{h['bk_host_id']}", "bk_host_inneripv6": "",
                     "bk_host_outeripv6": "", "bk_cloud_inst_id": "", "bk_agent_id": ""})
        
        logger.info(f"创建了 {len(host_list)} 个主机实例（存储在 cc_HostBase）")
        
        # 5. 创建主机-模块挂载关系（重构：按业务拓扑语义解析，不再硬编码模块 ID）
        # 挂载目标由 HOST_BINDING_SPEC 以 (业务, 集群名, 模块名) 表达，
        # seed_host_bindings() 运行时解析实际 bk_module_id/bk_set_id，
        # 目标缺失自动补全，先清旧绑定再落库，保证 re-migrate 幂等且无悬空。
        self.seed_host_bindings()
        

        logger.info("主线拓扑数据迁移完成!")


if __name__ == "__main__":
    # 直接运行迁移
    migrator = DatabaseMigrator()
    migrator.migrate()
