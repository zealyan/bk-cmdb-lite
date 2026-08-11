"""
内置鉴权包（最小内置方案，不依赖外部 IAM）

设计要点（对齐上游 bk-cmdb 数据形状）：
- 会话令牌名为 bk_token（上游同名），由 itsdangerous.TimedSerializer 签名，携带
  {bk_user_name, bk_supplier_account, bk_role}，max_age 即有效期。
- 身份头沿用上游习惯：bk_username / bk_supplier_account（网关注入或 cookie 解析）。
- 用户表 cc_UserBase 列名对齐上游 cc_User：bk_user_name / bk_supplier_account / bk_role(1=超管,2=普通)。
- skipLogin=True 时直接放行（无登录页）；=False 时要求有效 token。
- RBAC（模式 B）由 ENABLE_AUTH 总开关控制：关闭时全局短路放行（零回归），开启后走
  supplier 隔离 + 创建者自管 + 管理员全权 + 模型级策略（见 app/auth/{resource,policy,authorizer,manager,parser}）。
"""

from flask import jsonify
from app.config.settings import get_config
from app.auth.resource import Action
from app.auth.token import make_token, load_token
from app.auth.identity import (
    current_user_payload,
    current_user,
    current_supplier,
    is_authenticated,
    require_login,
)
from app.auth.user import init_user_table, bootstrap_admin
from app.auth.policy import init_policy_table

__all__ = [
    'make_token',
    'load_token',
    'current_user_payload',
    'current_user',
    'current_supplier',
    'is_authenticated',
    'require_login',
    'init_user_table',
    'bootstrap_admin',
    'init_policy_table',
    'ensure_creator_columns',
    'auth_filter',
    'no_permission',
]


def ensure_creator_columns():
    """启动时为所有实例表（自定义 ObjectBase 分表 + 内置 biz/set/module/host）补 creator 列。

    creator 用于「创建者自管」实例级判定（文档 §4.5）。
    新模型的实例表在 migrate.create_instance_table 已含该列；此处仅补齐历史/已存在表。
    """
    from app.db.executor import query_all, execute
    from app.service.instance_service import InstanceService
    from app.utils.logger import get_logger
    logger = get_logger('auth')
    try:
        rows = query_all(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cc_ObjectBase_0_pub_%'")
        tables = [r['name'] for r in rows]
        # 内置模型表也补齐（biz/set/module/host 复用同一套 owner 判定）
        tables.extend(InstanceService.BUILTIN_TABLE_MAP.values())
        for t in set(tables):
            try:
                cols = [c['name'] for c in query_all(f'PRAGMA table_info("{t}")')]
                if 'creator' not in cols:
                    execute(f'ALTER TABLE "{t}" ADD COLUMN creator VARCHAR DEFAULT \'\'')
                    logger.info(f'[ensure_creator_columns] 为 {t} 补 creator 列')
            except Exception as e:  # 单表失败不影响其余
                logger.warning(f'[ensure_creator_columns] 处理 {t} 失败: {e}')
    except Exception as e:
        logger.warning(f'[ensure_creator_columns] 扫描实例表失败: {e}')


def no_permission(permission):
    """统一无权限响应（HTTP 200 + BaseResp，bk_error_code=AUTH_ERR_NO_PERMISSION）。

    全站唯一的「无权限」出口：网关粗粒度门禁（auth_filter）与实例级 handler 检查
    （model.py 的 update/delete/batch_update）都收敛到此函数，保证同一 API 在任意
    路径下都返回完全一致的错误码、提示文案与 permission 载荷形状，供前端统一弹窗。
    """
    cfg = get_config()
    return jsonify({
        'result': False,
        'bk_error_code': cfg.AUTH_ERR_NO_PERMISSION,
        'bk_error_msg': cfg.AUTH_ERR_NO_PERMISSION_MSG,
        'permission': permission if permission is not None else {},
    }), 200


def auth_filter():
    """全局 before_request 粗粒度门禁（对应上游 apiserver authFilter）。

    - ENABLE_AUTH=False：直接放行（上游 EnableAuthorize 短路）
    - parse_route 返回 None 的路由：不拦截（零回归）
    - 创建在粗粒度层放开（实例创建后由创建者自动授权策略接管所有权）
    - 其余写操作：模型级 Authorize；无权返回 1302102
    """
    from flask import request
    from app.auth.parser import parse_route
    from app.auth.manager import coarse_authorize

    cfg = get_config()
    if not cfg.ENABLE_AUTH:
        return
    resources = parse_route(request)
    if not resources:
        return
    # 创建开放（与上游 RegisterResourceCreatorAction 哲学一致：所有权在写入时确立）
    if all(r.action == Action.CREATE for r in resources):
        return
    permission, ok = coarse_authorize(resources)
    if not ok:
        return no_permission(permission)
