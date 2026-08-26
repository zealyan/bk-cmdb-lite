"""
用户数据访问层（公共逻辑层）。

设计要点：
- 多方言：SQL 以 PostgreSQL 规范方言书写于 app/sql/user/*.sql，运行时由
  app.db.dialect 转译到当前数据库方言（settings.DATABASE_TYPE），再经
  app.db.executor（SQLAlchemy text 参数化）执行。切换 SQLite / PostgreSQL / MySQL
  无需改代码，只改配置。
- 公共复用：后端 API（app/api/v1/user.py -> app/service/user_service.py）与
  CLI（app/cli/cmdb.py）均调用本模块，不各自写 SQL，避免密码哈希 / 列名 /
  方言逻辑漂移。
- 安全：密码明文经 werkzeug 哈希存储，绝不落库明文；只读查询不返回密码列。

表：cc_UserBase（列名对齐上游 cc_User）
  bk_user_name        用户名（唯一）
  bk_supplier_account 供应商账户（多租户隔离，默认 0）
  bk_role             1=超级管理员 2=普通用户
  bk_password         werkzeug 哈希
  create_time         创建时间
"""
from datetime import datetime
from werkzeug.security import generate_password_hash

from app.db.executor import SQLExecutor
from app.db.sql_loader import load_sql
from app.db.dialect import dialect_converter
from app.config.settings import get_config, DialectType

TABLE = 'cc_UserBase'

ROLE_ADMIN = 1   # 超级管理员（全权）
ROLE_NORMAL = 2  # 普通用户

# SQL 文件书写所用的规范方言（DialectType.POSTGRESQL = 'postgres'）
_SOURCE_DIALECT = DialectType.POSTGRESQL.value


def _target_dialect() -> str:
    """当前数据库方言（sqlglot 书写名）。"""
    return {
        'sqlite': DialectType.SQLITE.value,        # 'sqlite'
        'postgresql': DialectType.POSTGRESQL.value,  # 'postgres'
        'mysql': DialectType.MYSQL.value,          # 'mysql'
    }.get(get_config().DATABASE_TYPE, DialectType.SQLITE.value)


def _sql(filename: str) -> str:
    """加载 SQL 文件并转译到当前方言（多方言核心）。"""
    raw = load_sql('user', filename)
    return dialect_converter.transpile(
        raw, source_dialect=_SOURCE_DIALECT, target_dialect=_target_dialect())


def _exe() -> SQLExecutor:
    """取「活引擎」执行器。

    模块级 sql_executor 在 import 时已绑定默认引擎；CLI 经 init_cli_db(--db)
    会 dispose 旧引擎并重建。此处每次调用重新解析当前引擎（get_engine() 返回
    db_engine 单例的活引擎），保证 API 与 CLI（含 --db 覆写）都命中正确库。
    """
    return SQLExecutor()


def _now() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def create_user(name: str, password: str, role: int = ROLE_NORMAL,
                supplier: str = None, password_hash: str = None) -> dict:
    """创建用户。

    Args:
        name:          用户名（bk_user_name），唯一
        password:      明文密码（经 werkzeug 哈希后存储）
        role:          1=超管 / 2=普通用户（默认 2）
        supplier:      供应商账户（默认 settings.DEFAULT_SUPPLIER='0'）
        password_hash: 预哈希密码（运维脚本传入，跳过明文哈希）

    Returns:
        新建用户行（不含密码）

    Raises:
        ValueError: 用户名为空 / 角色非法 / 用户名已存在
    """
    name = (name or '').strip()
    if not name:
        raise ValueError('用户名不能为空')
    if role not in (ROLE_ADMIN, ROLE_NORMAL):
        raise ValueError(f'非法角色值: {role}（仅 1=超管 / 2=普通用户）')
    if exists_user(name):
        raise ValueError(f'用户已存在: {name}')

    cfg = get_config()
    sup = supplier or cfg.DEFAULT_SUPPLIER
    pwd = password_hash or generate_password_hash(password)

    _exe().execute(_sql('create_user.sql'), {
        'bk_user_name': name,
        'bk_supplier_account': sup,
        'bk_role': role,
        'bk_password': pwd,
        'create_time': _now(),
    })
    return get_user(name)


def get_user(name: str):
    """按用户名取用户（不含密码）；不存在返回 None。"""
    return _exe().query_one(_sql('select_user.sql'), {'name': (name or '').strip()})


def list_users():
    """列出全部用户（不含密码）。"""
    return _exe().query_all(_sql('list_users.sql'), {})


def exists_user(name: str) -> bool:
    """用户名是否已存在。"""
    return _exe().query_one(_sql('select_user.sql'), {'name': (name or '').strip()}) is not None


def update_user_password(name: str, password: str = None, password_hash: str = None,
                         supplier: str = None) -> dict:
    """修改用户密码（明文经 werkzeug 哈希后存储）。

    Args:
        name:          用户名（bk_user_name），必填
        password:      明文新密码（与 password_hash 二选一，经 werkzeug 哈希）
        password_hash: 预哈希密码（运维脚本传入，跳过明文哈希）
        supplier:      供应商账户（默认 settings.DEFAULT_SUPPLIER='0'）

    Returns:
        更新后的用户行（不含密码）

    Raises:
        ValueError: 用户名为空 / 用户不存在 / password 与 password_hash 均未提供
    """
    name = (name or '').strip()
    if not name:
        raise ValueError('用户名不能为空')
    if not (password or password_hash):
        raise ValueError('必须提供 password 或 password_hash')
    if not exists_user(name):
        raise ValueError(f'用户不存在: {name}')

    cfg = get_config()
    sup = supplier or cfg.DEFAULT_SUPPLIER
    pwd = password_hash or generate_password_hash(password)

    _exe().execute(_sql('update_user_password.sql'), {
        'bk_password': pwd,
        'bk_user_name': name,
        'bk_supplier_account': sup,
    })
    return get_user(name)


def ensure_user_custom_supplier_column():
    """幂等迁移 user_custom 表，补 bk_supplier_account 列并按 user+supplier 隔离。

    对齐上游 cc_UserCustom 的 UNIQUE(user, supplier, key)。裁剪版此前仅按
    (user_name, config_key) 唯一且缺 supplier 列，导致不同租户同 user 的个性化
    配置会互相覆盖。SQLite 无法 ALTER 改 UNIQUE 约束，故通过「建新表→迁移数据
    →删旧表→改名」重建为含 supplier 的新 UNIQUE，保证隔离语义正确。

    非 SQLite 方言：信任 migrate.py 建表 DDL（已含新 UNIQUE + 列），此处跳过。
    """
    if get_config().DATABASE_TYPE != 'sqlite':
        return
    if _has_supplier_unique():
        return
    _exe().execute("""
        CREATE TABLE user_custom_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name VARCHAR NOT NULL,
            config_key VARCHAR NOT NULL,
            config_value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bk_supplier_account VARCHAR DEFAULT '0',
            UNIQUE(user_name, config_key, bk_supplier_account)
        )
    """, {})
    try:
        _exe().execute("""
            INSERT INTO user_custom_new (id, user_name, config_key, config_value, updated_at, bk_supplier_account)
            SELECT id, user_name, config_key, config_value, updated_at, '0' FROM user_custom
        """, {})
    except Exception:
        pass  # 空表等情况忽略
    _exe().execute("DROP TABLE user_custom", {})
    _exe().execute("ALTER TABLE user_custom_new RENAME TO user_custom", {})


def _has_supplier_unique() -> bool:
    """检测 user_custom 是否已存在包含 bk_supplier_account 的唯一索引。"""
    try:
        rows = _exe().query_all("PRAGMA index_list(user_custom)", {})
    except Exception:
        return False
    for r in rows:
        if not r.get('unique'):
            continue
        idx = r.get('name')
        if not idx:
            continue
        try:
            cols = _exe().query_all(f"PRAGMA index_info({idx})", {})
        except Exception:
            continue
        if any(c.get('name') == 'bk_supplier_account' for c in cols):
            return True
    return False
