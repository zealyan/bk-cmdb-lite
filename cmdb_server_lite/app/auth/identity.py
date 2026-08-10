"""
身份解析：四路来源，按优先级收敛到「当前用户名 / 供应商」

解析顺序（对齐上游 httpheader.GetUser 的取数习惯）：
  ① Bearer 头（Authorization: Bearer <bk_token>）
  ② bk_token cookie（上游同名透传）
  ③ 网关/开发注入头：bk_username / X-User
  ④ 配置默认用户（DEFAULT_USER，skipLogin / dev 场景）

注：本文件只负责「解析身份」，是否强制登录由 skipLogin + require_login 决定，
不在此处拒绝请求，保证 ENABLE_AUTH/RBAC 与登录强制解耦。
"""
from functools import wraps
from flask import request, jsonify
from app.config.settings import get_config
from app.auth.token import load_token


def current_user_payload():
    """若存在有效 token，返回其 payload dict；否则 None"""
    auth = request.headers.get('Authorization', '')
    token = None
    if auth.startswith('Bearer '):
        token = auth[7:].strip()
    else:
        token = request.cookies.get('bk_token')
    if token:
        return load_token(token)
    return None


def current_user():
    """当前用户名（字符串）"""
    p = current_user_payload()
    if p and p.get('bk_user_name'):
        return p['bk_user_name']
    u = request.headers.get('bk_username') or request.headers.get('X-User')
    if u:
        return u
    return get_config().DEFAULT_USER


def current_supplier():
    """当前供应商账户（默认 id0）"""
    p = current_user_payload()
    if p and p.get('bk_supplier_account'):
        return p['bk_supplier_account']
    s = request.headers.get('bk_supplier_account') or request.headers.get('X-Supplier-Account')
    if s:
        return s
    return get_config().DEFAULT_SUPPLIER


def is_authenticated():
    """是否已通过 token 认证（skipLogin 时视为已认证）"""
    if get_config().SKIP_LOGIN:
        return True
    return current_user_payload() is not None


def require_login():
    """装饰器：skipLogin=True 时直接放行；否则无有效 token 返回 401(HTTP 200+BaseResp)"""
    cfg = get_config()

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if cfg.SKIP_LOGIN:
                return f(*args, **kwargs)
            if current_user_payload() is None:
                return jsonify({
                    'result': False,
                    'bk_error_code': cfg.AUTH_ERR_UNAUTHORIZED,
                    'bk_error_msg': '未登录或登录已失效',
                }), 200
            return f(*args, **kwargs)
        return wrapper
    return decorator
