# -*- coding: utf-8 -*-
"""bk_property_type 权威常量定义。

本文件对标蓝鲸配置平台 Go 源码 ``src/common/definitions.go`` 中的 ``FieldTypes``
（definitions.go:995），作为 bk-cmdb-lite 后端**唯一**的 bk_property_type 权威来源：

    singlechar, longchar, int, float, enum, enummulti, date, time,
    objuser, organization, timezone, bool, list, table, innertable, enumquote

历史上 lite 中曾散落 ``user`` / ``singleasst`` / ``long`` / ``shortchar`` /
``char`` / ``text`` / ``double`` / ``datetime`` / ``textarea`` 等非 Go 类型，
容易与前端 / 校验侧认知不一致。

本文件**显性声明所有实际存在的 bk_property_type 常量**，分四类：
1. ``VALID_PROPERTY_TYPES``        —— 蓝鲸 Go 源码认可的 16 种合法类型（权威集合）。
2. ``LEGACY_PROPERTY_TYPE_ALIAS``  —— lite 历史命名，归一映射到 Go 类型
                                       （如 ``user`` -> ``objuser``）。
3. ``ASSOCIATION_PROPERTY_TYPES``  —— 关联类型（singleasst/multiasst/foreignkey），
                                       在 Go 中是合法的 bk_property_type，但**不作为
                                       实例表物理列**，关联数据存于 cc_InstAsst 分表。
4. ``OBJUSER_PROPERTY_TYPES`` / ``JSON_VALUE_PROPERTY_TYPES``
                                     —— 便于 service 层按类型做值处理的辅助集合。
                                     其中 objuser 在 MongoDB 中是纯逗号拼接字符串；
                                     organization 在 MongoDB 中是部门 ID 数组（落库 JSON 化）。

``get_sql_type()`` 仅认 ``VALID_PROPERTY_TYPES``（16 种），传入其它类型直接抛错；
历史 / 关联类型由调用方（migrate.create_instance_table）在调用前先归一或跳过，
从而保证「类型 -> SQL 列类型」的映射完全显式、无静默兜底。
"""

# ---------------------------------------------------------------------------
# bk_property_type 字符串常量（与 Go FieldTypes 一一对应）
# ---------------------------------------------------------------------------
PROPERTY_TYPE_SINGLECHAR = "singlechar"
PROPERTY_TYPE_LONGCHAR = "longchar"
PROPERTY_TYPE_INT = "int"
PROPERTY_TYPE_FLOAT = "float"
PROPERTY_TYPE_ENUM = "enum"
PROPERTY_TYPE_ENUMMULTI = "enummulti"
PROPERTY_TYPE_DATE = "date"
PROPERTY_TYPE_TIME = "time"
PROPERTY_TYPE_OBJUSER = "objuser"
PROPERTY_TYPE_ORGANIZATION = "organization"
PROPERTY_TYPE_TIMEZONE = "timezone"
PROPERTY_TYPE_BOOL = "bool"
PROPERTY_TYPE_LIST = "list"
PROPERTY_TYPE_TABLE = "table"
PROPERTY_TYPE_INNERTABLE = "innertable"
PROPERTY_TYPE_ENUMQUOTE = "enumquote"

# 全量合法类型集合（Go FieldTypes 的 Python 镜像，顺序与 definitions.go 一致）
VALID_PROPERTY_TYPES = (
    PROPERTY_TYPE_SINGLECHAR,
    PROPERTY_TYPE_LONGCHAR,
    PROPERTY_TYPE_INT,
    PROPERTY_TYPE_FLOAT,
    PROPERTY_TYPE_ENUM,
    PROPERTY_TYPE_ENUMMULTI,
    PROPERTY_TYPE_DATE,
    PROPERTY_TYPE_TIME,
    PROPERTY_TYPE_OBJUSER,
    PROPERTY_TYPE_ORGANIZATION,
    PROPERTY_TYPE_TIMEZONE,
    PROPERTY_TYPE_BOOL,
    PROPERTY_TYPE_LIST,
    PROPERTY_TYPE_TABLE,
    PROPERTY_TYPE_INNERTABLE,
    PROPERTY_TYPE_ENUMQUOTE,
)

# 数值类型集合：用于搜索 / 写入时把值做数值化（对齐 Go GoFieldTypes 的数值类）。
# 注：lite 早期曾用 long/double，但非 Go 合法类型且当前数据无此类，故不收录。
NUMERIC_PROPERTY_TYPES = (PROPERTY_TYPE_INT, PROPERTY_TYPE_FLOAT)

# objuser 在 MongoDB 中为「纯逗号拼接字符串」（如 "admin,test,zhangsan"），
# 与 singlechar/longchar 一样落库为 TEXT 纯字符串，读取/写入均不做 JSON 序列化，
# UI 端按逗号拆分（split(',')）展示、变更时数组用逗号拼接（join(',')）回写。
OBJUSER_PROPERTY_TYPES = (PROPERTY_TYPE_OBJUSER,)

# JSON 值类型集合（数组型）：如 organization 在 MongoDB 中为部门 ID 数组
#（bson.A / []interface{}），落库以 JSON 字符串保存，读取时解析回 Python 数组对象。
# 注意：objuser 是纯字符串，不属于此类。
JSON_VALUE_PROPERTY_TYPES = (PROPERTY_TYPE_ORGANIZATION,)

# ---------------------------------------------------------------------------
# 类型 -> SQL 列类型映射（SQLite 开发库；MySQL / PostgreSQL 见 docs/db.rule.md）
# ---------------------------------------------------------------------------
PROPERTY_TYPE_SQL_TYPE = {
    PROPERTY_TYPE_INT: "INTEGER",
    PROPERTY_TYPE_SINGLECHAR: "VARCHAR",
    PROPERTY_TYPE_LONGCHAR: "TEXT",
    PROPERTY_TYPE_FLOAT: "REAL",
    PROPERTY_TYPE_ENUM: "TEXT",
    PROPERTY_TYPE_ENUMMULTI: "TEXT",
    PROPERTY_TYPE_DATE: "DATE",
    PROPERTY_TYPE_TIME: "TIME",
    PROPERTY_TYPE_OBJUSER: "TEXT",
    PROPERTY_TYPE_ORGANIZATION: "TEXT",
    PROPERTY_TYPE_TIMEZONE: "VARCHAR",
    PROPERTY_TYPE_BOOL: "BOOLEAN",
    PROPERTY_TYPE_LIST: "TEXT",
    PROPERTY_TYPE_TABLE: "TEXT",
    PROPERTY_TYPE_INNERTABLE: "TEXT",
    PROPERTY_TYPE_ENUMQUOTE: "TEXT",
}

# ---------------------------------------------------------------------------
# lite 历史 / 关联类型（非 Go FieldTypes，但 lite 实际数据中存在，显式声明）
# ---------------------------------------------------------------------------
# lite 历史 / 关联类型字符串常量（便于全文检索与引用）
PROPERTY_TYPE_USER_LEGACY = "user"
PROPERTY_TYPE_MULTIASST_LEGACY = "multiasst"
PROPERTY_TYPE_FOREIGNKEY_LEGACY = "foreignkey"

# user 在蓝鲸 Go 源码中名为 objuser，lite 早期直接用了 user，这里显式归一。
LEGACY_PROPERTY_TYPE_ALIAS = {
    PROPERTY_TYPE_USER_LEGACY: PROPERTY_TYPE_OBJUSER,
}

# 关联类型：singleasst / multiasst / foreignkey 在 Go 中均为合法的 bk_property_type
# （见 metadata/attribute.go: case "foreignkey", "singleasst", "multiasst"），但
# 它们表达的是「本实例关联的另一个实例」，**不作为实例表的物理列**，关联数据存于
# cc_InstAsst 分表。建实例表时应直接跳过，不进入 get_sql_type 的 16 种校验。
ASSOCIATION_PROPERTY_TYPES = (
    PROPERTY_TYPE_MULTIASST_LEGACY,
    "singleasst",
    PROPERTY_TYPE_FOREIGNKEY_LEGACY,
)

# ---------------------------------------------------------------------------
# 分组 ID -> 标准显示名（CLI 与 migrate 共用，单一来源，避免漂移）
# ---------------------------------------------------------------------------
# 对齐上游 bk-cmdb 的非通用分组定义：
#   - admin_server/common/definitions.go        (BaseInfoName = "基础信息")
#   - src/scene_server/topo_server/logics/model/object.go:150  (自定义模型默认分组显示名)
#   - addPresetObjects.go / HostRow()           (auto/role/proc_port 分组)
# 仅作「按 ID 反查显示名」的兜底；CLI --group-auto-create 仅有 ID 列、
# 且未提供 bk_group_name 时才使用。若用户显式给了 bk_group_name，则以其为准。
KNOWN_GROUP_NAMES = {
    'default': '基础信息',
    'auto': '自动发现信息（需要安装agent）',
    'role': '角色',
    'proc_port': '监听信息',
}


def get_sql_type(prop_type):
    """根据 bk_property_type 返回对应的 SQL 列类型。

    仅接受 ``VALID_PROPERTY_TYPES`` 中的 16 种 Go 合法类型；传入其它类型将
    **直接抛错**，不再静默回退为 TEXT，以强制类型与 Go 源码保持一致。

    调用方（migrate.create_instance_table）负责在建表前处理非 16 种类型：
    - ``user`` 等历史命名先经 ``LEGACY_PROPERTY_TYPE_ALIAS`` 归一为 Go 类型；
    - ``singleasst`` / ``multiasst`` / ``foreignkey`` 等关联类型直接跳过（无物理列）。
    因此真正进入本函数的，必为 16 种之一。

    :param prop_type: 属性类型字符串
    :raises ValueError: 当 prop_type 不在合法类型集合中时
    """
    if prop_type not in PROPERTY_TYPE_SQL_TYPE:
        raise ValueError(
            f"非法的 bk_property_type: {prop_type!r}，必须是 Go definitions.go "
            f"FieldTypes 之一: {', '.join(VALID_PROPERTY_TYPES)}"
        )
    return PROPERTY_TYPE_SQL_TYPE[prop_type]


__all__ = [
    "PROPERTY_TYPE_SINGLECHAR",
    "PROPERTY_TYPE_LONGCHAR",
    "PROPERTY_TYPE_INT",
    "PROPERTY_TYPE_FLOAT",
    "PROPERTY_TYPE_ENUM",
    "PROPERTY_TYPE_ENUMMULTI",
    "PROPERTY_TYPE_DATE",
    "PROPERTY_TYPE_TIME",
    "PROPERTY_TYPE_OBJUSER",
    "PROPERTY_TYPE_ORGANIZATION",
    "PROPERTY_TYPE_TIMEZONE",
    "PROPERTY_TYPE_BOOL",
    "PROPERTY_TYPE_LIST",
    "PROPERTY_TYPE_TABLE",
    "PROPERTY_TYPE_INNERTABLE",
    "PROPERTY_TYPE_ENUMQUOTE",
    "VALID_PROPERTY_TYPES",
    "NUMERIC_PROPERTY_TYPES",
    "OBJUSER_PROPERTY_TYPES",
    "JSON_VALUE_PROPERTY_TYPES",
    "PROPERTY_TYPE_SQL_TYPE",
    "PROPERTY_TYPE_USER_LEGACY",
    "PROPERTY_TYPE_MULTIASST_LEGACY",
    "PROPERTY_TYPE_FOREIGNKEY_LEGACY",
    "LEGACY_PROPERTY_TYPE_ALIAS",
    "ASSOCIATION_PROPERTY_TYPES",
    "KNOWN_GROUP_NAMES",
    "get_sql_type",
    # 主线模型「名称字段」解析（详见下方 BUILTIN_NAME_FIELD / model_name_property）
    "BUILTIN_NAME_FIELD",
    "model_name_property",
]


# ---------------------------------------------------------------------------
# 主线模型「名称字段」解析
# 对齐上游 createDefaultAttrs：自定义主线模型（如 appsys/应用系统）以通用
# bk_inst_name 作为实例名称字段；而内置主线模型 set/module/biz 各自使用
# 专属名称字段（bk_set_name / bk_module_name / bk_biz_name），不共用 bk_inst_name。
# 唯一约束的「名称键」必须按模型取真实名称字段，否则（如硬编码 bk_inst_name）
# 会因内置模型无该属性而建不出规则，导致重名无校验。
# ---------------------------------------------------------------------------
BUILTIN_NAME_FIELD = {
    'set': 'bk_set_name',
    'module': 'bk_module_name',
    'biz': 'bk_biz_name',
}


def model_name_property(model_id, has_inst_name):
    """返回模型用于唯一约束的「名称属性 bk_property_id」。

    :param model_id: 模型 ID（如 'set' / 'module' / 'biz' / 'appsys'）
    :param has_inst_name: 该模型是否拥有 bk_inst_name 属性
    :return: 名称属性的 bk_property_id；无可用名称字段时返回 None（不建唯一约束）
    """
    if has_inst_name:
        return 'bk_inst_name'
    return BUILTIN_NAME_FIELD.get(model_id)
