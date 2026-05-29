"""
原生 SQL 执行器模块
执行查询/增删改/事务/参数化查询
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import text
from app.db.engine import get_engine, get_connection
from app.db.sql_loader import sql_loader

def _resolve_sql(sql_or_path: str) -> str:
    """
    解析 SQL 语句或文件路径
    
    Args:
        sql_or_path: SQL 语句或 SQL 文件路径（如 classification/select_classifications.sql）
        
    Returns:
        SQL 语句
    """
    # 判断是否为文件路径格式（包含 / 且以 .sql 结尾）
    if '/' in sql_or_path and sql_or_path.endswith('.sql'):
        parts = sql_or_path.rsplit('/', 1)
        if len(parts) == 2:
            module, filename = parts
            return sql_loader.load(module, filename)
    return sql_or_path

class SQLExecutor:
    """SQL 执行器"""
    
    def __init__(self):
        self.engine = get_engine()
    
    def execute(self, sql: str, params: Dict[str, Any] = None) -> Any:
        """
        执行 SQL 语句
        
        Args:
            sql: SQL 语句
            params: 参数化查询参数
            
        Returns:
            执行结果
        """
        conn = self.engine.connect()
        try:
            result = conn.execute(text(sql), params or {})
            conn.commit()
            return result
        finally:
            conn.close()
    
    def execute_many(self, sql: str, params_list: List[Dict[str, Any]]) -> None:
        """
        批量执行 SQL
        
        Args:
            sql: SQL 语句
            params_list: 参数列表
        """
        conn = self.engine.connect()
        try:
            for params in params_list:
                conn.execute(text(sql), params)
            conn.commit()
        finally:
            conn.close()
    
    def query_all(self, sql: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        查询所有结果
        
        Args:
            sql: SELECT 语句
            params: 查询参数
            
        Returns:
            结果列表
        """
        conn = self.engine.connect()
        try:
            result = conn.execute(text(sql), params or {})
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
        finally:
            conn.close()
    
    def query_one(self, sql: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        查询单条结果
        
        Args:
            sql: SELECT 语句
            params: 查询参数
            
        Returns:
            单条结果或 None
        """
        results = self.query_all(sql, params)
        return results[0] if results else None
    
    def query_count(self, sql: str, params: Dict[str, Any] = None) -> int:
        """
        查询数量
        
        Args:
            sql: COUNT 语句
            params: 查询参数
            
        Returns:
            数量
        """
        result = self.query_one(sql, params)
        return result.get('count', 0) if result else 0
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """
        插入数据
        
        Args:
            table: 表名
            data: 插入的数据
            
        Returns:
            影响的行数
        """
        columns = list(data.keys())
        values = list(data.values())
        placeholders = [f":{col}" for col in columns]
        
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        result = self.execute(sql, data)
        return result.rowcount if hasattr(result, 'rowcount') else 1
    
    def update(self, table: str, data: Dict[str, Any], where: Dict[str, Any]) -> int:
        """
        更新数据
        
        Args:
            table: 表名
            data: 更新的数据
            where: WHERE 条件
            
        Returns:
            影响的行数
        """
        set_clause = ', '.join([f"{col} = :{col}" for col in data.keys()])
        where_clause = ' AND '.join([f"{col} = :where_{col}" for col in where.keys()])
        
        params = {**data, **{f"where_{k}": v for k, v in where.items()}}
        sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        
        result = self.execute(sql, params)
        return result.rowcount if hasattr(result, 'rowcount') else 0
    
    def delete(self, table: str, where: Dict[str, Any]) -> int:
        """
        删除数据
        
        Args:
            table: 表名
            where: WHERE 条件
            
        Returns:
            影响的行数
        """
        where_clause = ' AND '.join([f"{col} = :{col}" for col in where.keys()])
        sql = f"DELETE FROM {table} WHERE {where_clause}"
        
        result = self.execute(sql, where)
        return result.rowcount if hasattr(result, 'rowcount') else 0
    
    def transaction(self, callbacks: List[callable]) -> Any:
        """
        执行事务
        
        Args:
            callbacks: 事务回调函数列表
            
        Returns:
            最后一个回调的返回值
        """
        conn = self.engine.connect()
        try:
            result = None
            with conn.begin():
                for callback in callbacks:
                    result = callback(conn)
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

# 全局执行器
sql_executor = SQLExecutor()

def execute(sql: str, params: Dict[str, Any] = None):
    """执行 SQL（支持 SQL 语句或文件路径）"""
    resolved_sql = _resolve_sql(sql)
    return sql_executor.execute(resolved_sql, params)

def query_all(sql: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """查询所有（支持 SQL 语句或文件路径）"""
    resolved_sql = _resolve_sql(sql)
    return sql_executor.query_all(resolved_sql, params)

def query_one(sql: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """查询一条（支持 SQL 语句或文件路径）"""
    resolved_sql = _resolve_sql(sql)
    return sql_executor.query_one(resolved_sql, params)

def insert(table: str, data: Dict[str, Any]) -> int:
    """插入数据"""
    return sql_executor.insert(table, data)

def update(table: str, data: Dict[str, Any], where: Dict[str, Any]) -> int:
    """更新数据"""
    return sql_executor.update(table, data, where)

def delete(table: str, where: Dict[str, Any]) -> int:
    """删除数据"""
    return sql_executor.delete(table, where)

def execute_many(sql: str, params_list: List[Dict[str, Any]]) -> None:
    """批量执行 SQL（支持 SQL 语句或文件路径）"""
    resolved_sql = _resolve_sql(sql)
    sql_executor.execute_many(resolved_sql, params_list)
