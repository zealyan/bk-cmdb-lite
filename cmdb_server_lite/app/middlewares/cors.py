"""
跨域中间件
"""

from flask import Flask
from flask_cors import CORS

def init_cors(app: Flask, config=None):
    """
    初始化 CORS
    
    Args:
        app: Flask 应用实例
        config: 配置对象
    """
    if config is None:
        from app.config.settings import get_config
        config = get_config()
    
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": config.CORS_ORIGINS,
                "methods": config.CORS_METHODS,
                "allow_headers": config.CORS_HEADERS
            }
        },
        supports_credentials=True
    )
