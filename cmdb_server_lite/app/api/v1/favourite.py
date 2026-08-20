"""
Host Favorite API（业务拓扑-主机列表「已收藏条件」）

路由（裁剪版 v1 风格，与上游 host_server /api/v3/hosts/favorites 对齐业务语义）：
  POST   /api/v1/hosts/favorites       创建收藏条件
  GET    /api/v1/hosts/favorites       查询当前用户收藏（?bk_biz_id= 业务过滤）
  DELETE /api/v1/hosts/favorites/<id>  删除收藏（按 id + 三层隔离条件）

隔离：bk_user / bk_supplier_account 由服务端从登录身份注入（不信任客户端头），
bk_biz_id 随请求携带。与上游一致，本端点不参与业务 RBAC（parser 不覆盖，fail-open）。
"""
from flask import Blueprint, jsonify, request
from app.service.favourite_service import (
    create_favourite, list_favourites, delete_favourite, update_favourite,
)
from app.auth.identity import current_user, current_supplier

favourite_bp = Blueprint('favourite', __name__)


def _ok(data=None, message=''):
    if data is None:
        data = {}
    return jsonify({
        'result': True,
        'bk_error_code': 0,
        'bk_error_msg': message,
        'data': data,
    }), 200


def _err(message, error_code=1199999):
    return jsonify({
        'result': False,
        'bk_error_code': error_code,
        'bk_error_msg': message,
    }), 200


def _biz_id(raw, default=0):
    try:
        return int(raw or default)
    except (TypeError, ValueError):
        return default


@favourite_bp.route('/favorites', methods=['POST'])
def create_fav():
    """创建收藏条件（user/supplier 服务端注入，biz_id 随 body 携带）。"""
    try:
        user = current_user()
        supplier = current_supplier()
        body = request.get_json(silent=True) or {}
        # 防御：绝不信任客户端伪造的 user/supplier 维度
        body.pop('bk_user', None)
        body.pop('bk_supplier_account', None)
        biz_id = _biz_id(body.get('bk_biz_id'))
        fav = create_favourite(user, supplier, biz_id, body)
        return _ok(fav, '收藏成功')
    except Exception as e:
        return _err(f'创建收藏失败: {str(e)}')


@favourite_bp.route('/favorites', methods=['GET'])
def list_fav():
    """查询当前用户 + 本租户 + 本业务的收藏（三层隔离）。"""
    try:
        user = current_user()
        supplier = current_supplier()
        biz_id = _biz_id(request.args.get('bk_biz_id'))
        items = list_favourites(user, supplier, biz_id)
        return _ok({'info': items})
    except Exception as e:
        return _err(f'查询收藏失败: {str(e)}')


@favourite_bp.route('/favorites/<fav_id>', methods=['DELETE'])
def delete_fav(fav_id):
    """删除收藏（按 id + 三层隔离条件；tom 无法删除 admin 的）。"""
    try:
        user = current_user()
        supplier = current_supplier()
        biz_id = _biz_id(request.args.get('bk_biz_id'))
        n = delete_favourite(fav_id, user, supplier, biz_id)
        if n == 0:
            return _err('收藏不存在或无权删除', 1199100)
        return _ok({'deleted': fav_id})
    except Exception as e:
        return _err(f'删除收藏失败: {str(e)}')


@favourite_bp.route('/favorites/<fav_id>', methods=['PUT'])
def update_fav(fav_id):
    """更新收藏条件（按 id + 三层隔离条件；tom 无法更新 admin 的）。"""
    try:
        user = current_user()
        supplier = current_supplier()
        biz_id = _biz_id(request.args.get('bk_biz_id'))
        body = request.get_json(silent=True) or {}
        # 防御：绝不信任客户端伪造的 user/supplier 维度
        body.pop('bk_user', None)
        body.pop('bk_supplier_account', None)
        n = update_favourite(fav_id, user, supplier, biz_id, body)
        if n == 0:
            return _err('收藏不存在或无权更新', 1199100)
        return _ok({'updated': fav_id})
    except Exception as e:
        return _err(f'更新收藏失败: {str(e)}')
