"""CLI 数据库访问层：复用 app.db.executor 的连接池 / 引擎 / 事务纪律。

设计要点：
- 通过覆写配置类的 DATABASE_NAME 实现 ``--db`` 覆盖（默认沿用 settings 的 cmdb_dev.db，
  与后端共用同一 SQLite 文件，满足设计文档 §2 C4 运行约束）。
- ``CliConn`` 封装单连接读写，配合 ``with c.conn.begin()`` 获得 SQLite DDL 事务原子性
  （设计文档 §5.11.4：SQLite 下 DDL 事务完全生效；PG/MySQL 退化为逐语句）。
- ``--dry-run`` 时命令层不调用执行器，仅打印 SQL。
"""

import os
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import text

from app.config.settings import get_config, config_by_env
from app.db.engine import init_db, db_engine
from app.cli.safety import validate_identifier

# lite 固定供应商账号（不支持多租户，设计文档 §1）
SUPPLIER = '0'


def init_cli_db(db_path: Optional[str] = None, env: str = 'development'):
    """初始化 CLI 使用的数据库引擎。

    - db_path 给定时，覆写所选环境的 DATABASE_NAME 为绝对路径（engine 据此拼接）。
    - 关闭 SQL 回显，避免 CLI 输出被 SQL 淹没。
    - 强制 dispose 任何在 import 阶段被提前创建的引擎（如 app.migrate.migrate 导入
      executor 时触发的默认引擎），确保 --db / echo 覆盖真正生效。
    复用 app.db.engine 的单例，保证与后端 API 共用同一连接池。
    """
    cfg_cls = config_by_env.get(env, config_by_env['default'])
    if db_path:
        cfg_cls.DATABASE_NAME = os.path.abspath(db_path)
    cfg_cls.SQLALCHEMY_ECHO = False
    db_engine.close()  # dispose 提前创建的引擎，强制按本配置重建
    init_db(cfg_cls)
    return db_engine.engine


class CliConn:
    """封装单个 SQLAlchemy 连接，提供参数化读写。"""

    def __init__(self, conn):
        self.conn = conn

    def exec(self, sql: str, params: Optional[dict] = None):
        return self.conn.execute(text(sql), params or {})

    def query_all(self, sql: str, params: Optional[dict] = None):
        result = self.conn.execute(text(sql), params or {})
        cols = result.keys()
        return [dict(zip(cols, row)) for row in result.fetchall()]

    def query_one(self, sql: str, params: Optional[dict] = None):
        rows = self.query_all(sql, params)
        return rows[0] if rows else None

    def commit(self):
        self.conn.commit()


@contextmanager
def cli_conn():
    """复用 app.db.engine 单例引擎的单连接上下文（SQLite StaticPool 复用底层连接）。"""
    from app.db.engine import db_engine
    conn = db_engine.engine.connect()
    try:
        yield CliConn(conn)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 表名解析（标识符安全）
# ---------------------------------------------------------------------------
def instance_table(obj_id: str) -> str:
    validate_identifier(obj_id)
    return f'cc_ObjectBase_0_pub_{obj_id}'


def assoc_table(obj_id: str) -> str:
    validate_identifier(obj_id)
    return f'cc_InstAsst_0_pub_{obj_id}'


def table_exists(conn: CliConn, name: str) -> bool:
    row = conn.query_one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=:n",
        {"n": name},
    )
    return row is not None


# ---------------------------------------------------------------------------
# 兜底建表（CLI 作为 migrate 补充；确保 cc_ObjectUnique / cc_ImportBatch 存在）
# 结构与 docs/新增模型数据库操作指南.md 八、及设计文档 §5.11.12 完全一致。
# ---------------------------------------------------------------------------
def ensure_object_unique_table(conn: CliConn):
    conn.exec(
        """CREATE TABLE IF NOT EXISTS cc_ObjectUnique (
            _id VARCHAR,
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bk_template_id INTEGER DEFAULT 0,
            bk_obj_id VARCHAR NOT NULL,
            keys TEXT,
            ispre BOOLEAN DEFAULT 0,
            bk_supplier_account VARCHAR DEFAULT '0',
            last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    )


def ensure_import_batch_table(conn: CliConn):
    conn.exec(
        """CREATE TABLE IF NOT EXISTS cc_ImportBatch (
            _id TEXT,
            batch_id TEXT,
            source_file TEXT,
            bk_obj_id VARCHAR,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            row_count INTEGER,
            reject_count INTEGER
        )"""
    )
