#!/usr/bin/env python3
"""
SQLAlchemy 调试工具
用于测试和验证 SQLAlchemy 连接池和原生 SQL 执行功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.engine import init_db, get_engine, get_connection
from app.db.executor import query_all, query_one, execute, insert, update, delete
from app.config.settings import DevelopmentConfig

def test_engine_initialization():
    """测试引擎初始化"""
    print("=" * 60)
    print("测试 1: SQLAlchemy 引擎初始化")
    print("=" * 60)
    
    config = DevelopmentConfig()
    engine = init_db(config)
    
    print(f"\n数据库类型: {config.DATABASE_TYPE}")
    print(f"数据库名称: {config.DATABASE_NAME}")
    print(f"引擎: {engine}")
    print(f"驱动: {engine.driver}")
    print("✅ 引擎初始化成功!")
    print()

def test_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("测试 2: 数据库连接")
    print("=" * 60)
    
    try:
        conn = get_connection()
        print(f"\n连接对象: {conn}")
        print(f"连接有效: {not conn.closed}")
        
        # 执行简单测试
        result = conn.execute("SELECT 1 as test")
        row = result.fetchone()
        print(f"测试查询结果: {row}")
        
        conn.close()
        print("✅ 连接测试成功!")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
    print()

def test_executor_query():
    """测试查询执行器"""
    print("=" * 60)
    print("测试 3: 查询执行器")
    print("=" * 60)
    
    try:
        # 测试 query_one
        print("\n测试 query_one:")
        result = query_one("SELECT 1 as test")
        print(f"结果: {result}")
        
        # 测试 query_all
        print("\n测试 query_all:")
        results = query_all("SELECT 1 as num UNION SELECT 2 UNION SELECT 3")
        print(f"结果列表: {results}")
        
        print("✅ 查询执行器测试成功!")
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    print()

def test_parameterized_query():
    """测试参数化查询"""
    print("=" * 60)
    print("测试 4: 参数化查询")
    print("=" * 60)
    
    try:
        # PostgreSQL 风格的命名参数
        sql = "SELECT :value1 as val1, :value2 as val2"
        result = query_one(sql, {"value1": "hello", "value2": "world"})
        print(f"\n参数化查询结果: {result}")
        
        # 测试多参数
        sql2 = "SELECT :name as user_name, :age as user_age"
        result2 = query_one(sql2, {"name": "张三", "age": 25})
        print(f"多参数查询结果: {result2}")
        
        print("✅ 参数化查询测试成功!")
    except Exception as e:
        print(f"❌ 参数化查询失败: {e}")
    print()

def test_raw_sql_execution():
    """测试原生 SQL 执行"""
    print("=" * 60)
    print("测试 5: 原生 SQL 执行")
    print("=" * 60)
    
    try:
        # 创建测试表
        print("\n创建测试表:")
        create_sql = """
        CREATE TABLE IF NOT EXISTS test_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100),
            value INTEGER
        )
        """
        execute(create_sql)
        print("✅ 测试表创建成功")
        
        # 插入测试数据
        print("\n插入测试数据:")
        insert_sql = "INSERT INTO test_table (name, value) VALUES (:name, :value)"
        
        for i in range(3):
            result = execute(insert_sql, {"name": f"test_{i}", "value": i * 10})
            print(f"插入第 {i+1} 条: {result}")
        
        # 查询数据
        print("\n查询数据:")
        results = query_all("SELECT * FROM test_table")
        for row in results:
            print(f"  {row}")
        
        # 更新数据
        print("\n更新数据:")
        update_sql = "UPDATE test_table SET value = :new_value WHERE name = :name"
        execute(update_sql, {"new_value": 999, "name": "test_0"})
        result = query_one("SELECT * FROM test_table WHERE name = :name", {"name": "test_0"})
        print(f"更新后: {result}")
        
        # 删除数据
        print("\n删除数据:")
        delete_sql = "DELETE FROM test_table WHERE name = :name"
        execute(delete_sql, {"name": "test_0"})
        results = query_all("SELECT * FROM test_table")
        print(f"删除后剩余: {len(results)} 条")
        
        # 清理测试表
        print("\n清理测试表:")
        execute("DROP TABLE IF EXISTS test_table")
        print("✅ 测试表已清理")
        
        print("\n✅ 原生 SQL 执行测试成功!")
    except Exception as e:
        print(f"❌ 原生 SQL 执行失败: {e}")
    print()

def test_connection_pool():
    """测试连接池"""
    print("=" * 60)
    print("测试 6: 连接池状态")
    print("=" * 60)
    
    engine = get_engine()
    pool = engine.pool
    
    print(f"\n连接池类型: {type(pool)}")
    
    if hasattr(pool, 'size'):
        print(f"当前连接数: {pool.size()}")
    if hasattr(pool, 'checked_in'):
        print(f"可用连接: {pool.checked_in()}")
    if hasattr(pool, 'checked_out'):
        print(f"已用连接: {pool.checked_out()}")
    
    print("✅ 连接池状态检查完成!")
    print()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("SQLAlchemy 调试工具")
    print("=" * 60 + "\n")
    
    try:
        test_engine_initialization()
        test_connection()
        test_executor_query()
        test_parameterized_query()
        test_raw_sql_execution()
        test_connection_pool()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
