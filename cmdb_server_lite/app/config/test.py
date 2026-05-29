# 测试环境配置

DEBUG = True
ENV = 'testing'

# 数据库配置 - SQLite for Test
DATABASE = {
    'type': 'sqlite',
    'name': 'cmdb_test.db',
    'pool_size': 5,
    'max_overflow': 10,
    'pool_recycle': 3600,
}

# 日志配置
LOG_LEVEL = 'DEBUG'
LOG_FILE = 'logs/test.log'

# CORS 配置
CORS_ORIGINS = ['*']

# API 配置
API_PREFIX = '/api/v1'
