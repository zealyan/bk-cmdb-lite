#!/usr/bin/env python3
"""
CLI 创建 bk-cmdb-lite 用户（普通用户 / 管理员）

用法:
  python3 add_user.py <username> <password> [--role 2|1] [--force]
    --role  1=超级管理员 2=普通用户(默认)
    --force 用户名已存在时强制更新密码

示例:
  python3 add_user.py tom tom123456          # 创建普通用户 tom
  python3 add_user.py admin2 Passw0rd --role 1

说明:
  - 密码使用 werkzeug generate_password_hash 哈希，与 authenticate() 校验完全一致
  - 复用 app.db.executor.insert，落库当前 settings 指定的数据库(默认 cmdb_dev.db)
"""
import argparse
import sys
from datetime import datetime

from werkzeug.security import generate_password_hash

from app.db.executor import query_one, insert
from app.auth.user import _sql, TABLE


def _exists(username):
    row = query_one(_sql('user_payload.sql'), {'bk_user_name': username})
    return bool(row)


def _update_password(username, password_hash):
    from app.db.executor import execute
    execute(
        f'UPDATE {TABLE} SET bk_password = :pwd WHERE bk_user_name = :name',
        {'pwd': password_hash, 'name': username},
    )


def _authenticate_ok(username, password):
    from app.auth.user import authenticate
    return bool(authenticate(username, password))


def add_user(username, password, role=2, force=False):
    if not username or not password:
        raise SystemExit('用户名和密码均不能为空')
    if role not in (1, 2):
        raise SystemExit('--role 仅支持 1(管理员) 或 2(普通用户)')

    password_hash = generate_password_hash(password)
    exists = _exists(username)

    if exists and not force:
        print(f'[跳过] 用户 "{username}" 已存在（如需更新密码请加 --force）')
        return False
    if exists and force:
        _update_password(username, password_hash)
        print(f'[更新] 用户 "{username}" 密码已更新')
    else:
        insert(TABLE, {
            'bk_user_name': username,
            'bk_supplier_account': '0',
            'bk_role': role,
            'bk_password': password_hash,
            'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
        print(f'[创建] 用户 "{username}" 已创建 (bk_role={role})')

    if _authenticate_ok(username, password):
        print(f'[校验] 账密 "{username}"/"{"*" * len(password)}" 登录校验通过 ✓')
    else:
        print('[警告] 登录校验未通过，请检查', file=sys.stderr)
    return True


def main():
    parser = argparse.ArgumentParser(description='创建 bk-cmdb-lite 用户')
    parser.add_argument('username', help='用户名')
    parser.add_argument('password', help='密码')
    parser.add_argument('--role', type=int, default=2, choices=[1, 2],
                        help='1=超级管理员 2=普通用户(默认)')
    parser.add_argument('--force', action='store_true',
                        help='用户名已存在时强制更新密码')
    args = parser.parse_args()
    add_user(args.username, args.password, args.role, args.force)


if __name__ == '__main__':
    main()
