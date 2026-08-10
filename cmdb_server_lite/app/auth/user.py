"""
用户 DAO：cc_UserBase 建表 + 初始管理员 + 校验

列名对齐上游 cc_User：
  bk_user_name        用户名（唯一）
  bk_supplier_account 供应商账户（多租户隔离，默认 0）
  bk_role             1=超级管理员 2=普通用户（对齐上游 bk_role 语义）
  bk_password         werkzeug 哈希，绝不存明文
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.db.executor import query_one, execute, insert
from app.config.settings import get_config

TABLE = 'cc_UserBase'


def init_user_table():
    """幂等建表"""
    execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            bk_user_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            bk_user_name        TEXT NOT NULL UNIQUE,
            bk_supplier_account TEXT NOT NULL DEFAULT '0',
            bk_role             INTEGER NOT NULL DEFAULT 2,
            bk_password         TEXT NOT NULL,
            create_time         TEXT
        )
    """)


def bootstrap_admin():
    """启动时确保初始管理员存在（bk_role=1）"""
    cfg = get_config()
    user = cfg.BOOTSTRAP_ADMIN_USER
    exists = query_one(f"SELECT bk_user_name FROM {TABLE} WHERE bk_user_name=:u", {'u': user})
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
    row = query_one(f"SELECT * FROM {TABLE} WHERE bk_user_name=:u", {'u': username})
    if not row:
        return None
    if not check_password_hash(row['bk_password'], password):
        return None
    return row


def get_user_payload(username):
    """取用户身份载荷（用于签发 token）"""
    row = query_one(
        f"SELECT bk_user_name, bk_supplier_account, bk_role FROM {TABLE} WHERE bk_user_name=:u",
        {'u': username},
    )
    if not row:
        return None
    return {
        'bk_user_name': row['bk_user_name'],
        'bk_supplier_account': row['bk_supplier_account'],
        'bk_role': row['bk_role'],
    }
