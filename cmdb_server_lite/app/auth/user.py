"""
用户 DAO：cc_UserBase 建表 + 初始管理员 + 校验

列名对齐上游 cc_User：
  bk_user_name        用户名（唯一）
  bk_supplier_account 供应商账户（多租户隔离，默认 0）
  bk_role             1=超级管理员 2=普通用户（对齐上游 bk_role 语义）
  bk_password         werkzeug 哈希，绝不存明文

SQL 多方言：所有语句以 PostgreSQL 规范方言书写于 app/sql/auth/*.sql，运行时由
app.db.dialect 转译到当前数据库方言（settings.DATABASE_TYPE），再经 app.db.executor
（SQLAlchemy text 参数化）执行。切换 SQLite / PostgreSQL / MySQL 无需改代码。
（对齐上一轮新增的公共逻辑层 app/db/user.py 的写法。）
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.db.executor import query_one, execute, insert
from app.db.sql_loader import load_sql
from app.db.dialect import dialect_converter
from app.config.settings import get_config, DialectType

TABLE = 'cc_UserBase'

# SQL 文件书写所用的规范方言（DialectType.POSTGRESQL = 'postgres'）
_SOURCE_DIALECT = DialectType.POSTGRESQL.value


def _target_dialect() -> str:
    """当前数据库方言（sqlglot 书写名）。"""
    return {
        'sqlite': DialectType.SQLITE.value,         # 'sqlite'
        'postgresql': DialectType.POSTGRESQL.value,  # 'postgres'
        'mysql': DialectType.MYSQL.value,           # 'mysql'
    }.get(get_config().DATABASE_TYPE, DialectType.SQLITE.value)


def _sql(filename: str) -> str:
    """加载 SQL 文件并转译到当前方言（多方言核心）。"""
    raw = load_sql('auth', filename)
    return dialect_converter.transpile(
        raw, source_dialect=_SOURCE_DIALECT, target_dialect=_target_dialect())


def init_user_table():
    """幂等建表（多方言 DDL，PostgreSQL 规范方言经转译执行）。"""
    execute(_sql('create_user_table.sql'), {})


def bootstrap_admin():
    """启动时确保初始管理员存在（bk_role=1）"""
    cfg = get_config()
    user = cfg.BOOTSTRAP_ADMIN_USER
    exists = query_one(_sql('user_payload.sql'), {'bk_user_name': user})
    if exists:
        return
    insert(TABLE, {
        'bk_user_name': user,
        'bk_supplier_account': cfg.DEFAULT_SUPPLIER,
        'bk_role': 1,
        'bk_password': generate_password_hash(cfg.BOOTSTRAP_ADMIN_PASS),
        'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })


def authenticate(username, password):
    """校验账密；成功返回用户行，失败返回 None"""
    row = query_one(_sql('authenticate.sql'), {'bk_user_name': username})
    if not row:
        return None
    if not check_password_hash(row['bk_password'], password):
        return None
    return row


def get_user_payload(username):
    """取用户身份载荷（用于签发 token）"""
    row = query_one(_sql('user_payload.sql'), {'bk_user_name': username})
    if not row:
        return None
    return {
        'bk_user_name': row['bk_user_name'],
        'bk_supplier_account': row['bk_supplier_account'],
        'bk_role': row['bk_role'],
    }
