"""
SQL 文件加载器
加载本地 .sql 文件并执行
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

class SQLLoader:
    """SQL 文件加载器"""
    
    def __init__(self, sql_dir: str = None):
        """
        初始化 SQL 加载器
        
        Args:
            sql_dir: SQL 文件目录,默认为 app/sql
        """
        if sql_dir is None:
            sql_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'sql'
            )
        self.sql_dir = Path(sql_dir)
        self._cache: Dict[str, str] = {}
    
    def load(self, module: str, filename: str) -> str:
        """
        加载 SQL 文件
        
        Args:
            module: 模块名 (如 user, order, common)
            filename: 文件名 (如 select_user.sql)
            
        Returns:
            SQL 内容
        """
        cache_key = f"{module}/{filename}"
        
        # 检查缓存
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 构建文件路径
        file_path = self.sql_dir / module / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"SQL file not found: {file_path}")
        
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 缓存
        self._cache[cache_key] = content
        
        return content
    
    def load_and_execute(self, module: str, filename: str, params: Dict = None) -> any:
        """
        加载并执行 SQL 文件
        
        Args:
            module: 模块名
            filename: 文件名
            params: 查询参数
            
        Returns:
            执行结果
        """
        sql = self.load(module, filename)
        from app.db.executor import sql_executor
        return sql_executor.execute(sql, params)
    
    def load_all_in_module(self, module: str) -> Dict[str, str]:
        """
        加载模块下所有 SQL 文件
        
        Args:
            module: 模块名
            
        Returns:
            文件名到内容的字典
        """
        module_dir = self.sql_dir / module
        if not module_dir.exists():
            return {}
        
        result = {}
        for sql_file in module_dir.glob("*.sql"):
            name = sql_file.stem
            result[name] = self.load(module, sql_file.name)
        
        return result
    
    def reload(self, module: str = None, filename: str = None) -> None:
        """
        重新加载 SQL 文件
        
        Args:
            module: 模块名,None 表示全部
            filename: 文件名,None 表示该模块全部
        """
        if module is None:
            # 清除全部缓存
            self._cache.clear()
        elif filename is None:
            # 清除模块缓存
            prefix = f"{module}/"
            self._cache = {
                k: v for k, v in self._cache.items()
                if not k.startswith(prefix)
            }
        else:
            # 清除单个文件缓存
            cache_key = f"{module}/{filename}"
            self._cache.pop(cache_key, None)

# 全局加载器
sql_loader = SQLLoader()

def load_sql(module: str, filename: str) -> str:
    """加载 SQL 文件"""
    return sql_loader.load(module, filename)

def execute_sql_file(module: str, filename: str, params: Dict = None) -> any:
    """执行 SQL 文件"""
    return sql_loader.load_and_execute(module, filename, params)
