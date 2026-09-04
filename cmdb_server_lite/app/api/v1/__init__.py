"""API v1 版本路由注册

前缀规范
--------
所有对外接口统一以 ``/api/v1`` 为前缀，且前缀**只在本文件的 register_blueprint
处声明**；各 blueprint 内部的 ``@bp.route`` 一律写相对路径，不再出现硬编码的
``/api`` 或 ``/api/v1``（早期 association_bp / user_bp 里的硬编码已清理）。

兼容路径
--------
association / unique / user 三个 blueprint 早期以两种非规范方式对外暴露：

- **上游 bk-cmdb 原始路径**：``POST /find/associationtype`` 这类动词在前的根路径，
  刻意对齐上游 topo_server，便于比对行为；
- **旧 /api 前缀**：``/api/usercustom/...``、``/api/users``（少了 ``/v1`` 一层）。

存量前端与外部调用方仍在使用这些路径，直接改前缀属破坏性变更，因此这三个 bp
采用**双注册**：

1. *兼容注册* —— 维持原有对外路径完全不变（deprecated，仅作过渡，勿新增调用）；
2. *规范注册* —— 以 ``/api/v1`` 前缀 + ``name='<bp>_v1'`` 再注册一份镜像，
   作为前端及新调用方的迁移目标。

同一 blueprint 重复注册依赖 Flask >= 2.0.1 的 ``name`` 参数（当前运行 2.3.3）；
``name`` 必须唯一，否则 Flask 抛
``ValueError: The name '<bp>' is already registered for a different blueprint``。

两次注册共用同一批视图函数，因此兼容路径与规范路径的行为、鉴权、返回体完全一致，
不存在实现漂移；待前端与外部调用方迁移完毕后，删除「兼容注册」区块即可收口。
"""

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
from .service_category import service_category_bp
from app.auth.views import auth_bp

# 规范前缀：本项目所有对外 API 的统一根前缀
API_V1_PREFIX = '/api/v1'


def register_v1_routes(app):
    """注册 v1 版本的所有路由"""
    # ========== 规范前缀注册（/api/v1/...）==========
    app.register_blueprint(common_bp, url_prefix=f'{API_V1_PREFIX}/common')
    app.register_blueprint(classification_bp, url_prefix=f'{API_V1_PREFIX}/classifications')
    app.register_blueprint(model_bp, url_prefix=f'{API_V1_PREFIX}/models')
    app.register_blueprint(instance_bp, url_prefix=f'{API_V1_PREFIX}/instances')
    app.register_blueprint(relation_bp, url_prefix=f'{API_V1_PREFIX}/relations')
    app.register_blueprint(topo_bp, url_prefix=f'{API_V1_PREFIX}/topo')
    app.register_blueprint(host_transfer_bp, url_prefix=f'{API_V1_PREFIX}/host/transfer')
    app.register_blueprint(auth_bp, url_prefix=f'{API_V1_PREFIX}/auth')
    app.register_blueprint(auth_manage_bp, url_prefix=f'{API_V1_PREFIX}/auth/manage')
    app.register_blueprint(favourite_bp, url_prefix=f'{API_V1_PREFIX}/hosts')
    app.register_blueprint(service_category_bp, url_prefix=f'{API_V1_PREFIX}/service/category')

    # ========== 兼容路径注册（deprecated，勿新增调用）==========
    # 上游 bk-cmdb topo_server 原始路径，无前缀：
    #   /find/<obj_id>、/find|create|update|delete/associationtype、
    #   /find|create|delete/objectassociation、/find|create|delete/instassociation、
    #   /associations/candidates
    app.register_blueprint(association_bp)
    # 上游 bk-cmdb 原始路径，无前缀：
    #   /find|create|update|delete/objectunique/object/<model_id>[/unique/<unique_id>]
    app.register_blueprint(unique_bp)
    # 旧前缀 /api（缺少 /v1 一层）：/api/usercustom/...、/api/users
    app.register_blueprint(user_bp, url_prefix='/api')

    # ========== 规范前缀镜像（上述三个 bp 的迁移目标）==========
    app.register_blueprint(association_bp, url_prefix=API_V1_PREFIX,
                           name='association_v1')
    app.register_blueprint(unique_bp, url_prefix=API_V1_PREFIX,
                           name='unique_v1')
    app.register_blueprint(user_bp, url_prefix=API_V1_PREFIX,
                           name='user_v1')
