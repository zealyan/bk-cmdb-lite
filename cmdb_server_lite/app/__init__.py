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
from app.auth import init_user_table, bootstrap_admin, init_policy_table, ensure_creator_columns, auth_filter
from app.service.favourite_service import init_favourite_table
from app.db.user import ensure_user_custom_supplier_column

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

    # 初始化内置鉴权：建 cc_UserBase 表 + 确保初始管理员存在
    init_user_table()
    bootstrap_admin()

    # 初始化 RBAC（模式 B）：建 cc_AuthPolicy 表 + 为实例表补 creator 列。
    # ENABLE_AUTH 默认 False，本步仅建表/补列，不改变任何鉴权行为（零回归）。
    init_policy_table()
    ensure_creator_columns()

    # 初始化 Host Favorite（业务拓扑-主机列表已收藏条件）表：三层隔离
    # user + bk_supplier_account + bk_biz_id，与上游 FavouriteMeta 一致。
    init_favourite_table()

    # 幂等为 user_custom 表补 bk_supplier_account 列（多租户隔离维度，对齐上游
    # cc_UserCustom 的 user + supplier 隔离）。已有库经 ALTER 加列兜底，可重复执行。
    ensure_user_custom_supplier_column()

    # 注册所有 v1 版本路由
    register_v1_routes(app)

    # 全局粗粒度门禁（对应上游 apiserver authFilter）；由 ENABLE_AUTH 总开关控制，
    # 关闭时直接放行，开启后对实例写端点做模型级鉴权。
    app.before_request(auth_filter)
    
    # 全局错误处理 - 统一返回 BaseResp 格式，与原项目一致
    # 业务异常一律返回 HTTP 200 + BaseResp（result:false + bk_error_code），
    # 由响应体内的 result 字段承载成功/失败，与 404/500 处理器保持一致，
    # 避免前端因 HTTP 非 2xx 把 friendly 的 bk_error_msg 当传输错误处理。
    @app.errorhandler(APIException)
    def handle_api_exception(e):
        return jsonify(e.to_dict()), 200
    
    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({
            'result': False,
            'bk_error_code': 1199019,
            'bk_error_msg': '请求路径不存在'
        }), 200
    
    @app.errorhandler(500)
    def handle_server_error(e):
        return jsonify({
            'result': False,
            'bk_error_code': 1199999,
            'bk_error_msg': '服务器内部错误'
        }), 200
    
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