# -*- coding: utf-8 -*-
"""bk_property_type 权威常量定义。

本文件对标蓝鲸配置平台 Go 源码 ``src/common/definitions.go`` 中的 ``FieldTypes``
（definitions.go:995），作为 bk-cmdb-lite 后端**唯一**的 bk_property_type 权威来源：

    singlechar, longchar, int, float, enum, enummulti, date, time,
    objuser, organization, timezone, bool, list, table, innertable, enumquote

历史上 lite 中曾散落 ``user`` / ``singleasst`` / ``long`` / ``shortchar`` /
``char`` / ``text`` / ``double`` / ``datetime`` / ``textarea`` 等非 Go 类型，
容易与前端 / 校验侧认知不一致。

本文件**显性声明所有实际存在的 bk_property_type 常量**，分三类：
1. ``VALID_PROPERTY_TYPES``        —— 蓝鲸 Go 源码认可的 16 种合法类型（权威集合）。
2. ``LEGACY_PROPERTY_TYPE_ALIAS``  —— lite 历史命名，归一映射到 Go 类型
                                       （如 ``user`` -> ``objuser``）。
3. ``ASSOCIATION_PROPERTY_TYPES``  —— 关联类型（singleasst/multiasst），无独立 Go
                                       字段类型，存关联实例 id，不进入 get_sql_type。

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
# lite 历史类型字符串常量（便于全文检索与引用）
PROPERTY_TYPE_USER_LEGACY = "user"
PROPERTY_TYPE_MULTIASST_LEGACY = "multiasst"

# user 在蓝鲸 Go 源码中名为 objuser，lite 早期直接用了 user，这里显式归一。
LEGACY_PROPERTY_TYPE_ALIAS = {
    PROPERTY_TYPE_USER_LEGACY: PROPERTY_TYPE_OBJUSER,
}

# 关联类型：singleasst / multiasst 在 Go 中没有对应 FieldType，它们表达的是
# 「本实例关联的另一个实例」，数据存于 cc_InstAsst 分表；建实例表时按关联实例
# id 建一列（INTEGER），不进入 get_sql_type 的 16 种校验。
ASSOCIATION_PROPERTY_TYPES = ("singleasst", "multiasst")
ASSOCIATION_PROPERTY_SQL_TYPE = {
    "singleasst": "INTEGER",
    "multiasst": "INTEGER",
}


def get_sql_type(prop_type):
    """根据 bk_property_type 返回对应的 SQL 列类型。

    仅接受 ``VALID_PROPERTY_TYPES`` 中的 16 种 Go 合法类型；传入其它类型
    （如 lite 历史上出现过的 ``user`` / ``singleasst`` / ``long`` / ``double`` /
    ``datetime`` 等）将**直接抛错**，不再静默回退为 TEXT，以强制类型与 Go
    源码保持一致。

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
    "PROPERTY_TYPE_SQL_TYPE",
    "get_sql_type",
]
