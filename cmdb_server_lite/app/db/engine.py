"""
SQLAlchemy 引擎管理模块
仅使用 SQLAlchemy 做连接池和原生 SQL 执行,禁用 ORM Model
"""

import os
from typing import Optional
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool, StaticPool
from app.config.settings import get_config, DatabaseType

class DatabaseEngine:
    """数据库引擎管理器"""
    
    _instance = None
    _engine = None
    _session_factory = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseEngine, cls).__new__(cls)
        return cls._instance
    
    def init_engine(self, config=None):
        """初始化数据库引擎"""
        if config is None:
            config = get_config()
        
        if self._engine is not None:
            return self._engine
        
        db_type = config.DATABASE_TYPE
        db_name = config.DATABASE_NAME
        
        if db_type == DatabaseType.SQLITE.value:
            # SQLite 数据库
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                db_name
            )
            db_url = f"sqlite:///{db_path}"
            
            # SQLite 使用 StaticPool 以支持多线程
            self._engine = create_engine(
                db_url,
                poolclass=StaticPool,
                connect_args={'check_same_thread': False},
                echo=config.SQLALCHEMY_ECHO
            )
        elif db_type == DatabaseType.POSTGRESQL.value:
            # PostgreSQL 数据库
            db_url = (
                f"postgresql://{config.DATABASE_USER}:{config.DATABASE_PASSWORD}"
                f"@{config.DATABASE_HOST}:{config.DATABASE_PORT}/{config.DATABASE_NAME}"
            )
            self._engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=config.SQLALCHEMY_POOL_SIZE,
                max_overflow=config.SQLALCHEMY_MAX_OVERFLOW,
                pool_recycle=config.SQLALCHEMY_POOL_RECYCLE,
                echo=config.SQLALCHEMY_ECHO
            )
        elif db_type == DatabaseType.MYSQL.value:
            # MySQL 数据库
            db_url = (
                f"mysql+pymysql://{config.DATABASE_USER}:{config.DATABASE_PASSWORD}"
                f"@{config.DATABASE_HOST}:{config.DATABASE_PORT}/{config.DATABASE_NAME}"
            )
            self._engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=config.SQLALCHEMY_POOL_SIZE,
                max_overflow=config.SQLALCHEMY_MAX_OVERFLOW,
                pool_recycle=config.SQLALCHEMY_POOL_RECYCLE,
                echo=config.SQLALCHEMY_ECHO
            )
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        # 创建会话工厂
        self._session_factory = sessionmaker(bind=self._engine)
        
        return self._engine
    
    @property
    def engine(self):
        """获取数据库引擎"""
        if self._engine is None:
            self.init_engine()
        return self._engine
    
    @property
    def session(self):
        """获取数据库会话"""
        if self._session_factory is None:
            self.init_engine()
        return scoped_session(self._session_factory)
    
    def get_connection(self):
        """获取数据库连接"""
        return self.engine.connect()
    
    def close(self):
        """关闭引擎"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None

# 全局单例
db_engine = DatabaseEngine()

def get_engine():
    """获取数据库引擎实例"""
    return db_engine.engine

def get_session():
    """获取数据库会话"""
    return db_engine.session

def get_connection():
    """获取数据库连接"""
    return db_engine.get_connection()

def init_db(config=None):
    """初始化数据库"""
    return db_engine.init_engine(config)

def close_db():
    """关闭数据库"""
    db_engine.close()
