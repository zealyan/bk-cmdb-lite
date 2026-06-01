"""
Flask 应用创建工厂
"""

from flask import Flask, jsonify
from app.config.settings import get_config
from app.db.engine import init_db
from app.middlewares.cors import init_cors
from app.utils.logger import setup_logger
from app.utils.exceptions import APIException
from app.api.v1 import register_v1_routes

def create_app(config=None):
    """
    创建 Flask 应用
    
    Args:
        config: 配置对象
        
    Returns:
        Flask 应用实例
    """
    app = Flask(__name__)
    
    # 加载配置
    if config is None:
        config = get_config()
    app.config.from_object(config)
    
    # 设置日志
    setup_logger('cmdb', config.LOG_LEVEL)
    
    # 初始化 CORS
    init_cors(app, config)
    
    # 初始化数据库
    init_db(config)
    
    # 注册所有 v1 版本路由
    register_v1_routes(app)
    
    # 全局错误处理
    @app.errorhandler(APIException)
    def handle_api_exception(e):
        return jsonify(e.to_dict()), e.status_code
    
    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({'detail': 'Not found'}), 404
    
    @app.errorhandler(500)
    def handle_server_error(e):
        return jsonify({'detail': 'Internal server error'}), 500
    
    # 根路径
    @app.route('/')
    def index():
        return jsonify({
            'message': 'CMDB Server Lite API',
            'version': '1.0.0',
            'endpoints': {
                'health': '/api/v1/common/health',
                'statistics': '/api/v1/common/statistics',
                'classifications': '/api/v1/classifications',
                'models': '/api/v1/models',
                'relations': '/api/v1/relations'
            }
        })
    
    return app