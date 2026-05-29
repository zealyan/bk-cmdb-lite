#!/usr/bin/env python3
"""
SQLglot 调试工具
用于测试和验证 sqlglot 的方言转译功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.dialect import dialect_converter, transpile, parse_sql, validate_sql
from app.config.settings import DialectType

def test_basic_transpile():
    """测试基础转译功能"""
    print("=" * 60)
    print("测试 1: 基础 PostgreSQL -> SQLite 转译")
    print("=" * 60)
    
    # PostgreSQL 语法
    postgres_sql = """
    SELECT 
        id,
        name,
        created_at,
        COALESCE(description, '') as desc
    FROM users
    WHERE active = true
    ORDER BY created_at DESC
    LIMIT 10 OFFSET 0
    """
    
    print("\n原始 PostgreSQL:")
    print(postgres_sql)
    
    # 转译为 SQLite
    sqlite_sql = transpile(postgres_sql, 'postgres', 'sqlite')
    print("\n转译为 SQLite:")
    print(sqlite_sql)
    
    # 验证语法
    is_valid = validate_sql(sqlite_sql, 'sqlite')
    print(f"\nSQLite 语法验证: {'✅ 有效' if is_valid else '❌ 无效'}")
    print()

def test_mysql_to_postgres():
    """测试 MySQL -> PostgreSQL 转译"""
    print("=" * 60)
    print("测试 2: MySQL -> PostgreSQL 转译")
    print("=" * 60)
    
    # MySQL 语法
    mysql_sql = """
    SELECT id, name, CONCAT(first_name, ' ', last_name) as full_name
    FROM customers
    WHERE status = 1 AND deleted_at IS NULL
    """
    
    print("\n原始 MySQL:")
    print(mysql_sql)
    
    # 转译为 PostgreSQL
    pg_sql = transpile(mysql_sql, 'mysql', 'postgres')
    print("\n转译为 PostgreSQL:")
    print(pg_sql)
    print()

def test_parse_and_modify():
    """测试解析和修改 AST"""
    print("=" * 60)
    print("测试 3: 解析 SQL 为 AST")
    print("=" * 60)
    
    sql = "SELECT id, name FROM users WHERE active = 1"
    print(f"\n原始 SQL: {sql}")
    
    ast = parse_sql(sql, 'postgres')
    if ast:
        print(f"AST 类型: {type(ast)}")
        print(f"AST 表示: {ast}")
    print()

def test_complex_query():
    """测试复杂查询转译"""
    print("=" * 60)
    print("测试 4: 复杂查询转译 (PostgreSQL -> SQLite)")
    print("=" * 60)
    
    # 包含子查询和聚合函数
    complex_sql = """
    SELECT 
        u.id,
        u.name,
        COUNT(o.id) as order_count,
        SUM(o.amount) as total_amount
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
    WHERE u.created_at >= '2024-01-01'
        AND u.status IN (1, 2, 3)
    GROUP BY u.id, u.name
    HAVING COUNT(o.id) > 5
    ORDER BY total_amount DESC
    LIMIT 20
    """
    
    print("\n原始 SQL:")
    print(complex_sql)
    
    sqlite_sql = transpile(complex_sql, 'postgres', 'sqlite')
    print("\n转译为 SQLite:")
    print(sqlite_sql)
    print()

def test_all_dialects():
    """测试所有支持的方言"""
    print("=" * 60)
    print("测试 5: 所有支持的方言")
    print("=" * 60)
    
    sql = "SELECT id, name FROM users WHERE active = true"
    dialects = ['postgres', 'mysql', 'sqlite', 'duckdb']
    
    for dialect in dialects:
        print(f"\n转译为 {dialect.upper()}:")
        try:
            result = transpile(sql, 'postgres', dialect)
            print(result)
        except Exception as e:
            print(f"转译失败: {e}")
    print()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("SQLglot 调试工具")
    print("=" * 60 + "\n")
    
    try:
        test_basic_transpile()
        test_mysql_to_postgres()
        test_parse_and_modify()
        test_complex_query()
        test_all_dialects()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
