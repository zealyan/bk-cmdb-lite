"""
全局基础配置
定义数据库默认参数、方言枚举等
"""

import os
from enum import Enum

class DatabaseType(Enum):
    """支持的数据库类型"""
    SQLITE = 'sqlite'
    POSTGRESQL = 'postgresql'
    MYSQL = 'mysql'
    DUCKDB = 'duckdb'

class DialectType(Enum):
    """sqlglot 支持的方言"""
    SQLITE = 'sqlite'
    POSTGRESQL = 'postgres'
    MYSQL = 'mysql'
    DUCKDB = 'duckdb'

# 全局基础配置
class BaseConfig:
    """基础配置类"""
    DEBUG = False
    TESTING = False
    ENV = 'base'
    
    # Flask 配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # 数据库配置
    DATABASE_TYPE = DatabaseType.SQLITE.value
    DATABASE_NAME = 'cmdb.db'
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATABASE_NAME)
    
    # SQLAlchemy 配置 (仅用于连接池)
    SQLALCHEMY_DATABASE_URI = None  # 由 db 模块动态构建
    SQLALCHEMY_POOL_SIZE = 5
    SQLALCHEMY_MAX_OVERFLOW = 10
    SQLALCHEMY_POOL_RECYCLE = 3600
    SQLALCHEMY_ECHO = False
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    LOG_FILE = os.path.join(LOG_DIR, 'app.log')
    
    # CORS 配置
    CORS_ORIGINS = ['*']
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_HEADERS = ['Content-Type', 'Authorization']
    
    # API 配置
    API_PREFIX = '/api/v1'
    API_VERSION = 'v1'
    
    # 分页配置
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 1000

# 开发环境配置
class DevelopmentConfig(BaseConfig):
    ENV = 'development'
    DEBUG = True
    DATABASE_TYPE = DatabaseType.SQLITE.value
    DATABASE_NAME = 'cmdb_dev.db'
    LOG_LEVEL = 'DEBUG'
    SQLALCHEMY_ECHO = True

# 测试环境配置
class TestingConfig(BaseConfig):
    ENV = 'testing'
    TESTING = True
    DATABASE_TYPE = DatabaseType.SQLITE.value
    DATABASE_NAME = 'cmdb_test.db'
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_NAME}"

# 生产环境配置
class ProductionConfig(BaseConfig):
    ENV = 'production'
    DEBUG = False
    DATABASE_TYPE = DatabaseType.POSTGRESQL.value
    LOG_LEVEL = 'WARNING'
    SQLALCHEMY_ECHO = False

# 配置字典
config_by_env = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(env=None):
    """获取配置类"""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    return config_by_env.get(env, config_by_env['default'])
