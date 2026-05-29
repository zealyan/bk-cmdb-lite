"""API v1 版本路由注册"""

from .common import common_bp
from .classification import classification_bp
from .model import model_bp
from .association import association_bp
from .relation import relation_bp
from .user import user_bp

def register_v1_routes(app):
    """注册 v1 版本的所有路由"""
    app.register_blueprint(common_bp, url_prefix='/api/v1/common')
    app.register_blueprint(classification_bp, url_prefix='/api/v1/classifications')
    app.register_blueprint(model_bp, url_prefix='/api/v1')  # 注册在 /api/v1 下，这样 /api/v1/models 和 /api/v1/instances 都能正常访问
    app.register_blueprint(relation_bp, url_prefix='/api/v1/relations')
    
    # 旧版 API 路径保持向后兼容
    app.register_blueprint(association_bp)
    app.register_blueprint(user_bp)