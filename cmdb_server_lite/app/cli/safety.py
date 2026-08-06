"""标识符安全（C1）——拼入 DDL 的标识符唯一强制校验入口。

所有命令在把用户输入拼进表名 / 列名 / 分组 ID / CSV 表头列名之前，
**必须**经本模块校验，禁止在命令内散落正则（设计文档 §7 实现要求 D）。
命名参数（:key）仅保护 VALUE，绝不保护标识符。
"""

import re

# 白名单：小写字母开头，仅含小写字母 / 数字 / 下划线
IDENTIFIER_RE = re.compile(r'^[a-z][a-z0-9_]*$')


class InvalidIdentifierError(ValueError):
    """标识符不满足 ^[a-z][a-z0-9_]*$"""


def validate_identifier(name: str) -> str:
    """校验标识符合法，非法直接抛 InvalidIdentifierError。"""
    if not isinstance(name, str) or not IDENTIFIER_RE.match(name):
        raise InvalidIdentifierError(
            f"非法标识符: {name!r}，必须满足 ^[a-z][a-z0-9_]*$"
            f"（小写字母开头，仅含小写字母 / 数字 / 下划线）"
        )
    return name


def quote_ident(name: str) -> str:
    """校验并转义内部双引号后加双引号包裹，安全拼入 DDL。

    例：'bk_switch' -> '"bk_switch"'。内部 \" 转义为 \"\"（防御性，白名单已排除）。
    仅用于**用户提供的标识符**（bk_obj_id / bk_property_id / 分组 ID / CSV 表头列名）。
    """
    validate_identifier(name)
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def quote_ident_raw(name: str) -> str:
    """不加白名单校验地包裹标识符（转义内部双引号）。

    用于**含可信固定前缀**的表名，如 cc_ObjectBase_0_pub_{bk_obj_id}：
    其中前缀 cc_ObjectBase_0_pub_ 来自代码常量（非用户输入，含大写），仅后缀
    bk_obj_id 经 validate_identifier 校验。此处只做引号包裹，避免误拒合法表名。
    """
    escaped = str(name).replace('"', '""')
    return f'"{escaped}"'
