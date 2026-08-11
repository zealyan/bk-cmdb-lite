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

    # ── 内置鉴权配置（最小内置方案，不使用外部 IAM）──
    # skipLogin=True 时后端不强制登录、current_user 回落默认 admin，前端不显示登录页。
    # 部署时设 CMDB_SKIP_LOGIN=false 即开启登录页 + token 强制。
    SKIP_LOGIN = os.environ.get('CMDB_SKIP_LOGIN', 'true').lower() == 'true'
    # token 有效期（秒），用 itsdangerous.TimedSerializer.max_age 实现
    TOKEN_MAX_AGE = int(os.environ.get('CMDB_TOKEN_MAX_AGE', '3600'))
    # 无身份时的回落用户 / 供应商（dev / skipLogin 场景）
    DEFAULT_USER = os.environ.get('CMDB_DEFAULT_USER', 'admin')
    DEFAULT_SUPPLIER = os.environ.get('CMDB_DEFAULT_SUPPLIER', '0')
    # 启动时自动创建的初始管理员（bk_role=1 超管）
    BOOTSTRAP_ADMIN_USER = os.environ.get('CMDB_ADMIN_USER', 'admin')
    BOOTSTRAP_ADMIN_PASS = os.environ.get('CMDB_ADMIN_PASS', 'admin')
    # 身份相关错误码（对齐上游：result:false + bk_error_code，HTTP 仍 200）
    AUTH_ERR_UNAUTHORIZED = 1302100   # 未登录 / 登录失效
    AUTH_ERR_BAD_CREDENTIAL = 1302101 # 用户名或密码错误
    AUTH_ERR_NO_PERMISSION = 1302102  # 无操作权限（CCNoPermission）
    AUTH_ERR_NO_PERMISSION_MSG = '无操作权限'  # 无权限统一提示文案（全站唯一）

    # ── RBAC 总开关（模式 B：内置轻量权限）──
    # ENABLE_AUTH=False（默认）时全局短路放行，行为与现状完全一致（零回归）。
    # 设为 true 开启内置 RBAC：supplier 隔离 + 创建者自管 + 管理员全权 + 模型级策略。
    ENABLE_AUTH = os.environ.get('CMDB_ENABLE_AUTH', 'false').lower() == 'true'

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
