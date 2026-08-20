# 开发环境配置

DEBUG = True
ENV = 'development'

# 数据库配置 - SQLite for Dev
DATABASE = {
    'type': 'sqlite',
    'name': 'cmdb_dev.db',
    'pool_size': 5,
    'max_overflow': 10,
    'pool_recycle': 3600,
}

# 日志配置
LOG_LEVEL = 'DEBUG'
LOG_FILE = 'logs/dev.log'

# CORS 配置
CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:8080']

# API 配置
API_PREFIX = '/api/v1'
