"""
鉴权蓝图：登录 / 当前用户 / 登出

路由前缀 /api/v1/auth：
  POST /login   账号密码 → {bk_token, bk_user_name, bk_role}
  GET  /me      返回当前身份（skipLogin 时返回默认 admin + skipLogin:true；未登录返回 1302100）
  POST /logout  无状态 token 无需服务端销毁，前端清 localStorage 即可

响应统一 BaseResp（result + bk_error_code + bk_error_msg + data），
与项目其它端点一致；HTTP 状态恒 200，由 result 承载成败。
"""
from flask import Blueprint, request, jsonify
from app.auth.user import authenticate, get_user_payload, bootstrap_admin, init_user_table
from app.auth.token import make_token
from app.auth.identity import current_user_payload
from app.config.settings import get_config

auth_bp = Blueprint('auth', __name__)


def _ok(data):
    return jsonify({'result': True, 'bk_error_code': 0, 'bk_error_msg': '', 'data': data}), 200


def _err(message, code):
    return jsonify({'result': False, 'bk_error_code': code, 'bk_error_msg': message, 'data': {}}), 200


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('bk_user_name') or data.get('username')
    password = data.get('bk_password') or data.get('password')
    if not username or not password:
        return _err('用户名或密码不能为空', get_config().AUTH_ERR_BAD_CREDENTIAL)

    row = authenticate(username, password)
    if not row:
        return _err('用户名或密码错误', get_config().AUTH_ERR_BAD_CREDENTIAL)

    payload = get_user_payload(username)
    token = make_token(payload)
    return _ok({
        'bk_token': token,
        'bk_user_name': payload['bk_user_name'],
        'bk_role': payload['bk_role'],
    })


@auth_bp.route('/me', methods=['GET'])
def me():
    cfg = get_config()
    if cfg.SKIP_LOGIN:
        return _ok({
            'bk_user_name': cfg.DEFAULT_USER,
            'bk_supplier_account': cfg.DEFAULT_SUPPLIER,
            'bk_role': 1,
            'skipLogin': True,
        })
    payload = current_user_payload()
    if payload:
        return _ok({
            'bk_user_name': payload['bk_user_name'],
            'bk_supplier_account': payload.get('bk_supplier_account'),
            'bk_role': payload.get('bk_role'),
            'skipLogin': False,
        })
    return _err('未登录或登录已失效', cfg.AUTH_ERR_UNAUTHORIZED)


@auth_bp.route('/logout', methods=['POST'])
def logout():
    # 无状态 token：服务端无需销毁，前端清除 localStorage/cookie 即失效
    return _ok({})
