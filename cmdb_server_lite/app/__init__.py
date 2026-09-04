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
from app.service.service_category_service import init_service_category_table
from app.db.user import ensure_user_custom_supplier_column

import decimal
import uuid
from datetime import date, time as _dtime, datetime as _dt, timedelta
from flask.json.provider import DefaultJSONProvider


class CMDBJSONProvider(DefaultJSONProvider):
    """扩展默认 JSON 序列化，跨方言兼容各数据库驱动返回的特殊类型。

    同一逻辑列在不同方言驱动下返回不同的 Python 类型，本项目（Flask 默认
    DefaultJSONProvider）不原生支持其中部分类型，会在搜索/详情接口整包
    ``jsonify`` 时抛出 ``Object of type X is not JSON serializable``。本 Provider
    在序列化层统一兜底，**与底层方言无关**，覆盖三库实际返回：

    =========  ============================  =============================  =============================
    逻辑列      MySQL (pymysql)               SQLite (SQLAlchemy)           PostgreSQL (psycopg2)
    =========  ============================  =============================  =============================
    TIME        ``datetime.timedelta``        ``str``（文本，天然无 T）      ``datetime.time``
    DATE        ``datetime.date``            ``str``                        ``datetime.date``
    TIMESTAMP   ``datetime.datetime``         ``str``（无 T）                ``datetime.datetime``
    NUMERIC     ``decimal.Decimal``          ``str`` / ``Decimal``          ``decimal.Decimal``
    bytea/BLOB  ``bytes``                     ``bytes``                      ``memoryview``  ← PG 特有
    =========  ============================  =============================  =============================

    兜底规则：
    - ``timedelta``（MySQL 的 TIME 列）→ ``HH:MM:SS[.ffffff]`` 字符串；
    - ``datetime`` → ``%Y-%m-%d %H:%M:%S``（去掉 isoformat 自带的 T，与用户输入/
      SQLite 文本格式统一）；``date``/``time`` → ``isoformat()``（本身无 T）；
    - ``Decimal`` → ``float``；``bytes``/``memoryview`` → utf-8/hex；
      ``UUID``/``set``/``frozenset`` → 可序列化形式。
    """

    def default(self, o):
        if isinstance(o, timedelta):
            total = o.total_seconds()
            sign = '-' if total < 0 else ''
            total = abs(total)
            hours, rem = divmod(int(total), 3600)
            minutes, seconds = divmod(rem, 60)
            if o.microseconds:
                return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}.{o.microseconds:06d}"
            return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"
        if isinstance(o, _dt):
            # 去掉 isoformat() 自带的 'T' 分隔符，统一为 MySQL 风格
            # "YYYY-MM-DD HH:MM:SS"，与用户输入的时间文本（多为
            # datetime-local/文本输入，无 'T'）保持一致，避免前后端展示差异。
            return o.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(o, (date, _dtime)):
            return o.isoformat()
        if isinstance(o, decimal.Decimal):
            return float(o)
        if isinstance(o, (bytes, memoryview)):
            # PostgreSQL 的 bytea 经 psycopg2 返回 memoryview（非 bytes），
            # 先归一为 bytes 再按 utf-8/hex 处理，否则会触发
            # "Object of type memoryview is not JSON serializable"。
            b = bytes(o)
            try:
                return b.decode('utf-8')
            except UnicodeDecodeError:
                return b.hex()
        if isinstance(o, (set, frozenset)):
            return list(o)
        if isinstance(o, uuid.UUID):
            return str(o)
        return super().default(o)


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

    # 初始化服务分类表（业务拓扑-服务分类管理，cc_ServiceCategory），幂等建表。
    init_service_category_table()

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

    # 其余 HTTP 异常（405/400/408/413/415/429/3xx 等）统一兜底为 BaseResp + HTTP 200，
    # 与 404/500/APIException 处理器保持同一响应结构（result + bk_error_code +
    # bk_error_msg），避免前端把 friendly 的错误信息当传输层错误处理。
    # Flask 按异常类最精确匹配：404/500 已注册专属 handler，这里只补其它状态码。
    from werkzeug.exceptions import HTTPException
    from app.utils.exceptions import http_error_meta

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        code, msg = http_error_meta(e.code)
        return jsonify({
            'result': False,
            'bk_error_code': code,
            'bk_error_msg': msg,
            'data': {}
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
    
    # 注册自定义 JSON 序列化器（跨方言兜底）：MySQL TIME→timedelta、PG/SQLite
    # TIME→datetime.time、PG bytea→memoryview、Decimal/UUID/set 等类型，避免任意
    # 方言驱动返回的特殊类型在接口序列化时崩溃（如原 MySQL 的
    # "timedelta is not JSON serializable"）。
    app.json = CMDBJSONProvider(app)

    return app