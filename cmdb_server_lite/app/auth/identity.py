"""
身份解析：按「可配置来源顺序」收敛到当前用户名 / 供应商

解析来源（顺序与开关由 settings 控制，见 AUTH_PAYLOAD_ORDER / AUTH_BEARER / AUTH_TOKEN_QUERY）：
  COOKIE     —— 浏览器会话 lite_bk_token cookie（本 lite 自定义名，非上游同名）
  BEARER     —— Authorization: Bearer <bk_token>（受 AUTH_BEARER 开关控制）
  X_LITE_TOKEN —— 自定义头 X-Lite-Token（本项目自定义，非上游内置；agentos 网关对 X- 前缀头透传）
  QUERY      —— URL 查询参数 ?lite_bk_token（受 AUTH_TOKEN_QUERY 开关控制；本 lite 自定义名，非上游同名）

默认有效顺序为 COOKIE → X_LITE_TOKEN。
注：本文件只负责「解析身份」，是否强制登录由 SKIP_LOGIN + require_login 决定，
不在此处拒绝请求，保证 ENABLE_AUTH/RBAC 与登录强制解耦。
"""
from functools import wraps
from flask import request, jsonify
from app.config.settings import get_config
from app.auth.token import load_token


def current_user_payload():
    """若存在有效 token，返回其 payload dict；否则 None

    按 settings.AUTH_PAYLOAD_ORDER 的顺序逐来源尝试，取第一个能通过签名校验的载荷
    （first-valid-wins）。顺序本身只决定优先级与尝试顺序，不影响正确性：某来源被部署
    网关污染/剥离导致校验失败时，自动落到下一个有效来源。

    各来源是否启用：
      COOKIE     —— 始终启用（浏览器会话 lite_bk_token cookie）
      BEARER     —— 受 AUTH_BEARER 开关控制（默认关闭：规避 agentos 网关注入/覆盖
                     Authorization 平台 token 的污染）
      X_LITE_TOKEN —— 始终启用（自定义头 X-Lite-Token: <token>，网关对 X- 前缀头透传）
      QUERY      —— 受 AUTH_TOKEN_QUERY 开关控制（默认关闭：避免 token 进 URL 日志/
                    浏览器历史造成泄露）
    """
    cfg = get_config()
    order = cfg.AUTH_PAYLOAD_ORDER

    def _extract(kind):
        if kind == 'COOKIE':
            return request.cookies.get('lite_bk_token')
        if kind == 'BEARER':
            if not cfg.AUTH_BEARER:
                return None
            auth = request.headers.get('Authorization', '')
            return auth[7:].strip() if auth.startswith('Bearer ') else None
        if kind == 'X_LITE_TOKEN':
            return request.headers.get('X-Lite-Token')
        if kind == 'QUERY':
            if not cfg.AUTH_TOKEN_QUERY:
                return None
            return request.args.get('lite_bk_token')
        return None

    for kind in order:
        token = _extract(kind)
        if token:
            payload = load_token(token)
            if payload:
                return payload
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
