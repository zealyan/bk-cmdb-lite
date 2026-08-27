"""
sqlglot 方言转译模块
处理多数据库方言的 SQL 语法适配
"""

import re
import sqlglot
from typing import Optional, Dict, List, Any
from app.config.settings import DatabaseType, DialectType

class DialectConverter:
    """方言转换器"""
    
    def __init__(self, target_dialect: str = None):
        """
        初始化方言转换器
        
        Args:
            target_dialect: 目标数据库方言,默认为 SQLite
        """
        self.target_dialect = target_dialect or DialectType.SQLITE.value
    
    def transpile(self, sql: str, source_dialect: str = None, target_dialect: str = None,
                  identify: bool = False) -> str:
        """
        转译 SQL 语句到目标方言
        
        Args:
            sql: 原始 SQL 语句
            source_dialect: 源方言,默认为 postgres
            target_dialect: 目标方言
            identify: 是否强制引用所有标识符（保留大小写），用于跨库标识符一致性
            
        Returns:
            转译后的 SQL 语句
        """
        target = target_dialect or self.target_dialect
        
        try:
            # 使用 sqlglot 转译 SQL
            result = sqlglot.transpile(
                sql,
                read=source_dialect or DialectType.POSTGRESQL.value,
                write=target,
                pretty=True,
                identify=identify,
            )
            return result[0] if result else sql
        except Exception as e:
            print(f"[DialectConverter] Transpile error: {e}")
            return sql
    
    def parse(self, sql: str, dialect: str = None) -> Optional[Any]:
        """
        解析 SQL 语句为 AST
        
        Args:
            sql: SQL 语句
            dialect: 方言
            
        Returns:
            SQL AST 对象
        """
        target_dialect = dialect or self.target_dialect
        
        try:
            return sqlglot.parse(sql, read=target_dialect)[0]
        except Exception as e:
            print(f"[DialectConverter] Parse error: {e}")
            return None
    
    def to_json(self, sql: str, dialect: str = None) -> str:
        """
        将 SQL 转换为 JSON 表示
        
        Args:
            sql: SQL 语句
            dialect: 方言
            
        Returns:
            JSON 字符串
        """
        ast = self.parse(sql, dialect)
        if ast:
            return ast.sql()
        return sql
    
    @staticmethod
    def validate_syntax(sql: str, dialect: str = None) -> bool:
        """
        验证 SQL 语法
        
        Args:
            sql: SQL 语句
            dialect: 方言
            
        Returns:
            语法是否有效
        """
        try:
            sqlglot.parse(sql, read=dialect)
            return True
        except:
            return False

# 全局方言转换器
dialect_converter = DialectConverter()

def transpile(sql: str, source_dialect: str = None, target_dialect: str = None) -> str:
    """转译 SQL"""
    return dialect_converter.transpile(sql, source_dialect, target_dialect)

def parse_sql(sql: str, dialect: str = None):
    """解析 SQL"""
    return dialect_converter.parse(sql, dialect)

def validate_sql(sql: str, dialect: str = None) -> bool:
    """验证 SQL 语法"""
    return DialectConverter.validate_syntax(sql, dialect)


# ---------------------------------------------------------------------------
# 执行层方言适配（sqlite 源码 -> 当前目标方言）
# ---------------------------------------------------------------------------
from app.config.settings import get_config, DatabaseType
from sqlalchemy import inspect

# DatabaseType -> sqlglot 方言名
_DBTYPE_TO_SQLGLOT = {
    DatabaseType.SQLITE.value: 'sqlite',
    DatabaseType.POSTGRESQL.value: 'postgres',
    DatabaseType.MYSQL.value: 'mysql',
    DatabaseType.DUCKDB.value: 'duckdb',
}

# upsert 已产出最终方言 SQL 的标记，跳过二次转译
_UPSERT_MARKERS = ('ON DUPLICATE KEY UPDATE', 'ON CONFLICT')

_adapt_cache = {}


def current_dialect() -> str:
    """返回当前引擎对应的 sqlglot 方言名（默认 sqlite）。"""
    try:
        return _DBTYPE_TO_SQLGLOT.get(get_config().DATABASE_TYPE, 'sqlite')
    except Exception:
        return 'sqlite'


def adapt_sql(sql: str) -> str:
    """把 SQLite 风格 SQL 转译为当前目标方言，供执行层统一调用。

    - 目标为 sqlite：恒等返回（零开销、零回归）。
    - SQLite 专属 ``INSERT OR REPLACE``：sqlglot 无法转译，在此重写为目标方言
      upsert（mysql ``ON DUPLICATE KEY UPDATE`` / postgres ``ON CONFLICT ... DO UPDATE``），
      冲突目标列由 ``_CONFLICT_MAP`` 按表名映射，未列出的表默认以 ``id`` 为主键。
    - 目标为 mysql/postgres：经 sqlglot 转译标识符引号（" -> ` / "）、
      AUTOINCREMENT -> AUTO_INCREMENT / SERIAL、CAST AS TEXT -> CHAR、类型映射等。
    - 已含 upsert 标记的 SQL（ON DUPLICATE KEY UPDATE / ON CONFLICT）视为最终方言
      SQL，跳过二次转译。
    - 转译失败（sqlglot 无法解析）时回退原 SQL，不影响执行。
    结果按 (sql, dialect) 缓存。
    """
    target = current_dialect()
    if target == 'sqlite':
        return sql
    # SQLite 专属语法：INSERT OR REPLACE（sqlglot 无法转译），重写后再落地
    if _INSERT_OR_REPLACE_RE.search(sql):
        return _rewrite_insert_or_replace(sql, target)
    up = sql.upper()
    if any(m in up for m in _UPSERT_MARKERS):
        return sql
    key = (sql, target)
    cached = _adapt_cache.get(key)
    if cached is not None:
        return cached
    try:
        # identify=True：强制引用所有标识符并保留大小写，使未加引号的表/列名
        # （如 FROM cc_ObjDes）也变为 "cc_ObjDes"（PG）/ `cc_ObjDes`（MySQL），
        # 与加引号的 DDL 保持一致；PG 据此保留混合大小写，匹配应用层字面量。
        out = dialect_converter.transpile(sql, source_dialect='sqlite',
                                          target_dialect=target, identify=True)
    except Exception:
        out = sql
    if target == 'mysql':
        # MySQL 要求 VARCHAR 必须带长度（PG/SQLite 允许无长度），补默认 255。
        out = re.sub(r'\bVARCHAR\b(?!\s*\()', 'VARCHAR(255)', out)
    _adapt_cache[key] = out
    return out


# ---------------------------------------------------------------------------
# INSERT OR REPLACE -> 目标方言 upsert（sqlglot 无法处理该 SQLite 专属语法）
# ---------------------------------------------------------------------------
# 冲突目标列：按表名映射到唯一/主键列。
#   - 未列出的表默认以 id 为主键冲突列（覆盖绝大多数 cc_* 表与动态实例分表）。
#   - 业务表（bk_*_id 为主键）与复合唯一键表需显式列出，否则 PG 会报
#     "no unique or exclusion constraint matching the ON CONFLICT specification"。
_CONFLICT_MAP: Dict[str, List[str]] = {
    'cc_ApplicationBase': ['bk_biz_id'],
    'cc_SetBase': ['bk_set_id'],
    'cc_ModuleBase': ['bk_module_id'],
    'cc_HostBase': ['bk_host_id'],
    'cc_ModuleHostConfig': ['bk_host_id', 'bk_module_id'],
    'cc_ObjClassification': ['id'],
    'cc_ObjDes': ['bk_obj_id'],
    'cc_ObjAttDes': ['bk_obj_id', 'bk_property_id'],
    'cc_AsstDes': ['bk_asst_id'],
    'cc_ObjAsst': ['bk_obj_asst_id'],
    'cc_PropertyGroup': ['id'],
    'cc_InstAsst_0_pub': ['id'],
    'cc_ObjectUnique': ['id'],
}


_INSERT_OR_REPLACE_RE = re.compile(
    r'INSERT\s+OR\s+REPLACE\s+INTO\s+("?[\w]+"?)\s*\(([^)]*)\)\s*VALUES\s*\(([^)]*)\)',
    re.IGNORECASE | re.DOTALL,
)


def _split_idents(raw: str) -> List[str]:
    """把 "a, \"b\", `c`" 解析为 ['a', 'b', 'c']（去引号、去空白、去空项）。"""
    out = []
    for part in raw.split(','):
        part = part.strip().strip('"').strip('`').strip()
        if part:
            out.append(part)
    return out


def _rewrite_insert_or_replace(sql: str, dialect: str) -> str:
    """把 ``INSERT OR REPLACE INTO tbl (cols) VALUES (ph)`` 重写为目标方言 upsert。

    - mysql：``INSERT ... VALUES (...) ON DUPLICATE KEY UPDATE c=VALUES(c)...``
      （依赖任意唯一/主键，无需指定列，最稳）。
    - postgres：``INSERT ... VALUES (...) ON CONFLICT (冲突列) DO UPDATE SET c=EXCLUDED.c...``
      冲突列取自 ``_CONFLICT_MAP``，缺省为 ``id``。
    """
    m = _INSERT_OR_REPLACE_RE.search(sql)
    if not m:
        return sql
    tbl = m.group(1).strip().strip('"').strip('`')
    cols = _split_idents(m.group(2))
    vals = m.group(3).strip()
    qtbl = _q(tbl)
    qcols = ', '.join(_q(c) for c in cols)
    if dialect == 'mysql':
        assign = ', '.join(f'{_q(c)}=VALUES({_q(c)})' for c in cols)
        return (f'INSERT INTO {qtbl} ({qcols}) VALUES ({vals}) '
                f'ON DUPLICATE KEY UPDATE {assign}')
    conflict_cols = _CONFLICT_MAP.get(tbl, ['id'])
    qconflict = ', '.join(_q(c) for c in conflict_cols)
    assign = ', '.join(f'{_q(c)}=EXCLUDED.{_q(c)}' for c in cols)
    return (f'INSERT INTO {qtbl} ({qcols}) VALUES ({vals}) '
            f'ON CONFLICT ({qconflict}) DO UPDATE SET {assign}')


# ---------------------------------------------------------------------------
# 内省（取代 sqlite_master / PRAGMA table_info，跨库通用）
# ---------------------------------------------------------------------------
def table_exists(name: str) -> bool:
    """表是否存在（跨库通用）。"""
    try:
        return inspect(_engine()).has_table(name)
    except Exception:
        return False


def _engine():
    from app.db.engine import db_engine
    return db_engine.engine


def list_table_names() -> list:
    """列出当前库全部表名（跨库通用）。"""
    try:
        return inspect(_engine()).get_table_names()
    except Exception:
        return []


def get_column_names(name: str) -> list:
    """返回表全部列名（跨库通用，取代 PRAGMA table_info）。表不存在时返回 []。"""
    try:
        return [c['name'] for c in inspect(_engine()).get_columns(name)]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# upsert（等价 SQLite INSERT OR REPLACE，三库通用）
# ---------------------------------------------------------------------------
def _q(name: str) -> str:
    """标识符引号：mysql 反引号，其余双引号（与 sqlglot 转译结果一致）。"""
    if current_dialect() == 'mysql':
        return '`' + str(name).replace('`', '``') + '`'
    return '"' + str(name).replace('"', '""') + '"'


def upsert(table: str, columns: list, placeholders: list, conflict: str = 'id') -> str:
    """三库通用 upsert，等价 SQLite「INSERT OR REPLACE INTO」。

    Args:
        table: 表名（未引号化）。
        columns: 列名列表（未引号化），如 ['bk_obj_id', 'bk_obj_name']。
        placeholders: 命名参数列表，如 [':bk_obj_id', ':bk_obj_name']。
        conflict: PG 的 ON CONFLICT 目标列（默认 'id'；非 id 主键表需显式传，
                  如 cc_ApplicationBase 传 'bk_biz_id'）。

    Returns:
        完整 INSERT 语句（已含 VALUES(...)）。
    """
    qcols = ', '.join(_q(c) for c in columns)
    qtable = _q(table)
    vals = ', '.join(placeholders)
    target = current_dialect()
    if target == 'sqlite':
        return f'INSERT OR REPLACE INTO {qtable} ({qcols}) VALUES ({vals})'
    if target == 'mysql':
        assign = ', '.join(f'{_q(c)}=VALUES({_q(c)})' for c in columns)
        return f'INSERT INTO {qtable} ({qcols}) VALUES ({vals}) ON DUPLICATE KEY UPDATE {assign}'
    # postgresql
    assign = ', '.join(f'{_q(c)}=EXCLUDED.{_q(c)}' for c in columns)
    return f'INSERT INTO {qtable} ({qcols}) VALUES ({vals}) ON CONFLICT ({_q(conflict)}) DO UPDATE SET {assign}'
