"""
sqlglot 方言转译模块
处理多数据库方言的 SQL 语法适配
"""

import sqlglot
from typing import Optional, Dict, List
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
    
    def transpile(self, sql: str, source_dialect: str = None, target_dialect: str = None) -> str:
        """
        转译 SQL 语句到目标方言
        
        Args:
            sql: 原始 SQL 语句
            source_dialect: 源方言,默认为 postgres
            target_dialect: 目标方言
            
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
                pretty=True
            )
            return result[0] if result else sql
        except Exception as e:
            print(f"[DialectConverter] Transpile error: {e}")
            return sql
    
    def parse(self, sql: str, dialect: str = None) -> sqlglot.AST:
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
