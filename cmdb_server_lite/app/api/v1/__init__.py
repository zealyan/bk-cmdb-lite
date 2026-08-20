"""API v1 版本路由注册"""

from .common import common_bp
from .classification import classification_bp
from .model import model_bp, instance_bp
from .association import association_bp
from .relation import relation_bp
from .user import user_bp
from .unique import unique_bp
from .topo import topo_bp
from .host_transfer import host_transfer_bp
from .auth_manage import auth_manage_bp
from .favourite import favourite_bp
from app.auth.views import auth_bp

def register_v1_routes(app):
    """注册 v1 版本的所有路由"""
    app.register_blueprint(common_bp, url_prefix='/api/v1/common')
    app.register_blueprint(classification_bp, url_prefix='/api/v1/classifications')
    app.register_blueprint(model_bp, url_prefix='/api/v1/models')
    app.register_blueprint(instance_bp, url_prefix='/api/v1/instances')
    app.register_blueprint(relation_bp, url_prefix='/api/v1/relations')
    app.register_blueprint(topo_bp, url_prefix='/api/v1/topo')
    app.register_blueprint(host_transfer_bp, url_prefix='/api/v1/host/transfer')
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(auth_manage_bp, url_prefix='/api/v1/auth/manage')
    app.register_blueprint(favourite_bp, url_prefix='/api/v1/hosts')

    # 旧版 API 路径保持向后兼容
    app.register_blueprint(association_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(unique_bp)