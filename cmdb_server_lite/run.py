"""
项目统一启动入口
"""

import os
from dotenv import load_dotenv

# 加载环境变量
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    load_dotenv(env_file)

# 设置环境
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')

from app import create_app
from app.config.settings import get_config

if __name__ == '__main__':
    config = get_config(FLASK_ENV)
    app = create_app(config)
    
    print(f"Starting CMDB Server Lite in {FLASK_ENV} mode...")
    print(f"Database: {config.DATABASE_TYPE} - {config.DATABASE_NAME}")
    
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=config.DEBUG
    )
