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
        config: CORS 配置
    """
    if config is None:
        from app.config.settings import get_config
        cfg = get_config()
        config = {
            'origins': cfg.CORS_ORIGINS,
            'methods': cfg.CORS_METHODS,
            'headers': cfg.CORS_HEADERS
        }
    
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": config['origins'],
                "methods": config['methods'],
                "allow_headers": config['headers']
            }
        },
        supports_credentials=True
    )
