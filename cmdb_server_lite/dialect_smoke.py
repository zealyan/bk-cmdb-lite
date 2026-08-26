#!/usr/bin/env python3
"""三库方言冒烟测试：在 SQLite / PostgreSQL / MySQL 上跑完整 migrate 并验证建表/upsert/查询。

用法：
    python3.11 dialect_smoke.py --dialect sqlite
    python3.11 dialect_smoke.py --dialect postgresql
    python3.11 dialect_smoke.py --dialect mysql

每个方言在独立进程中运行（settings 在 import 期读取环境变量），避免单例/缓存串味。
"""
import os
import sys
import argparse
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# ── 在导入 app 之前确定方言与连接参数（settings 在 import 期读取环境变量）──
parser = argparse.ArgumentParser()
parser.add_argument('--dialect', required=True, choices=['sqlite', 'postgresql', 'mysql'])
args = parser.parse_args()
DIALECT = args.dialect

if DIALECT == 'sqlite':
    os.environ['CMDB_DATABASE_TYPE'] = 'sqlite'
    DB_NAME = 'cmdb_smoke_sqlite.db'
elif DIALECT == 'postgresql':
    os.environ['CMDB_DATABASE_TYPE'] = 'postgresql'
    os.environ['CMDB_DB_HOST'] = '127.0.0.1'
    os.environ['CMDB_DB_PORT'] = '5432'
    os.environ['CMDB_DB_USER'] = 'postgres'
    os.environ['CMDB_DB_PASSWORD'] = 'postgres'
    DB_NAME = 'cmdb_smoke_pg'
elif DIALECT == 'mysql':
    os.environ['CMDB_DATABASE_TYPE'] = 'mysql'
    os.environ['CMDB_DB_HOST'] = '127.0.0.1'
    os.environ['CMDB_DB_PORT'] = '3306'
    os.environ['CMDB_DB_USER'] = 'root'
    os.environ['CMDB_DB_PASSWORD'] = 'root'
    DB_NAME = 'cmdb_smoke_mysql'

# 关闭 SQL echo，聚焦结果
os.environ['FLASK_ENV'] = 'development'


def provision_server_db():
    """在 PG/MySQL 服务端预建测试库（sqlite 跳过）。"""
    if DIALECT == 'postgresql':
        import sqlalchemy
        admin = sqlalchemy.create_engine(
            'postgresql://postgres:postgres@127.0.0.1:5432/postgres')
        with admin.connect() as c:
            c.execution_options(isolation_level='AUTOCOMMIT')
            c.execute(sqlalchemy.text(f'DROP DATABASE IF EXISTS {DB_NAME}'))
            c.execute(sqlalchemy.text(f'CREATE DATABASE {DB_NAME}'))
        print(f'[provision] PG 库 {DB_NAME} 已建')
    elif DIALECT == 'mysql':
        import sqlalchemy
        admin = sqlalchemy.create_engine(
            'mysql+pymysql://root:root@127.0.0.1:3306/')
        with admin.connect() as c:
            c.execute(sqlalchemy.text(f'DROP DATABASE IF EXISTS {DB_NAME}'))
            c.execute(sqlalchemy.text(f'CREATE DATABASE {DB_NAME}'))
        print(f'[provision] MySQL 库 {DB_NAME} 已建')


def main():
    if DIALECT != 'sqlite':
        provision_server_db()

    # 覆盖开发库名 + 重置引擎单例（必须在首次引擎访问前）
    import app.config.settings as settings
    settings.DevelopmentConfig.DATABASE_NAME = DB_NAME
    if DIALECT == 'sqlite':
        db_path = ROOT / DB_NAME
        if db_path.exists():
            db_path.unlink()
    from app.db.engine import db_engine
    db_engine._engine = None
    db_engine._session_factory = None

    from app.db.dialect import current_dialect, list_table_names, get_column_names, adapt_sql
    from app.migrate.migrate import DatabaseMigrator
    from app.db.executor import execute, query_all

    print(f'[dialect] current_dialect = {current_dialect()}')
    expected = {'sqlite': 'sqlite', 'postgresql': 'postgres', 'mysql': 'mysql'}[DIALECT]
    assert current_dialect() == expected, f'方言不匹配: {current_dialect()} != {expected}'

    m = DatabaseMigrator()
    print('[migrate] 开始完整迁移 ...')
    m.migrate()
    print('[migrate] 完成')

    # 验证核心表存在
    tables = list_table_names()
    required = ['cc_ObjClassification', 'cc_ObjDes', 'cc_ObjAttDes', 'cc_AsstDes',
                'cc_ObjAsst', 'cc_ObjectUnique', 'cc_ApplicationBase', 'cc_SetBase',
                'cc_ModuleBase', 'cc_HostBase', 'cc_ModuleHostConfig']
    missing = [t for t in required if t not in tables]
    assert not missing, f'缺失核心表: {missing}'
    print(f'[check] 核心表齐全（共 {len(tables)} 张表）')

    # 验证种子数据（分类）
    cls = query_all("SELECT * FROM cc_ObjClassification")
    assert cls, 'cc_ObjClassification 无种子数据'
    print(f'[check] 分类种子数 = {len(cls)}')

    # 验证 upsert 语义（INSERT OR REPLACE -> 目标方言）：同 id 覆盖应只留 1 行
    # （cc_ObjectUnique 主键为 id，冲突列即 id；与 SQLite INSERT OR REPLACE 行为一致）
    execute("INSERT OR REPLACE INTO cc_ObjectUnique "
            "(_id, id, bk_obj_id, keys, ispre, bk_supplier_account) "
            "VALUES (:_id, :id, :bk_obj_id, :keys, '1', '0')",
            {"_id": "smoke_uq", "id": 900001, "bk_obj_id": "smoke",
             "keys": "[{\"key_kind\":\"property\",\"key_id\":\"name\"}]"})
    execute("INSERT OR REPLACE INTO cc_ObjectUnique "
            "(_id, id, bk_obj_id, keys, ispre, bk_supplier_account) "
            "VALUES (:_id, :id, :bk_obj_id, :keys, '1', '0')",
            {"_id": "smoke_uq", "id": 900001, "bk_obj_id": "smoke",
             "keys": "[{\"key_kind\":\"property\",\"key_id\":\"ip\"}]"})
    cnt = query_all("SELECT COUNT(*) AS c FROM cc_ObjectUnique WHERE _id = :_id",
                    {"_id": "smoke_uq"})
    assert cnt[0]['c'] == 1, f'upsert 未去重，实际行数={cnt[0]["c"]}'
    print('[check] INSERT OR REPLACE -> upsert 去重语义正确（PG ON CONFLICT / MySQL ON DUPLICATE KEY）')

    # 验证动态实例表创建（create_instance_table 走 adapt_sql）
    m.create_instance_table('smoke_model')
    assert f'cc_ObjectBase_0_pub_smoke_model' in list_table_names(), '动态实例表未创建'
    cols = get_column_names('cc_ObjectBase_0_pub_smoke_model')
    assert 'id' in cols and 'bk_inst_id' in cols, '动态实例表缺列'
    print(f'[check] 动态实例表 cc_ObjectBase_0_pub_smoke_model 列数 = {len(cols)}')

    # 验证 CAST AS TEXT（mysql->CHAR / pg->TEXT）能执行
    if DIALECT == 'postgresql':
        # pg 保留 TEXT，直接跑
        r = query_all('SELECT LOWER(CAST("bk_obj_id" AS TEXT)) AS v '
                      'FROM cc_ObjDes LIMIT 1')
    elif DIALECT == 'mysql':
        r = query_all('SELECT LOWER(CAST(`bk_obj_id` AS CHAR)) AS v '
                      'FROM cc_ObjDes LIMIT 1')
    else:
        r = query_all('SELECT LOWER(CAST("bk_obj_id" AS TEXT)) AS v '
                      'FROM cc_ObjDes LIMIT 1')
    print(f'[check] CAST 查询可执行（采样 bk_obj_id = {r[0]["v"] if r else None}）')

    # 清理（sqlite 文件删除）
    if DIALECT == 'sqlite':
        db_engine.close()
        p = ROOT / DB_NAME
        if p.exists():
            p.unlink()
    print(f'\n=== {DIALECT.upper()} 冒烟测试 PASS ===')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'\n!!! {DIALECT.upper()} 冒烟测试 FAIL: {e}')
        traceback.print_exc()
        sys.exit(1)
