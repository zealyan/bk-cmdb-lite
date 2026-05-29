# 生产环境配置

DEBUG = False
ENV = 'production'

# 数据库配置 - PostgreSQL for Production
DATABASE = {
    'type': 'postgresql',
    'host': 'localhost',
    'port': 5432,
    'database': 'cmdb_prod',
    'user': 'cmdb_user',
    'password': 'your_password_here',
    'pool_size': 20,
    'max_overflow': 40,
    'pool_recycle': 3600,
}

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/prod.log'

# CORS 配置
CORS_ORIGINS = ['https://your-production-domain.com']

# API 配置
API_PREFIX = '/api/v1'
