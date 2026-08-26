# -*- coding: utf-8 -*-
"""鉴权管理 API（用户 + 策略 + 按场景批量授权）。

按 docs/权限配置使用手册.md / 权限设计方案.md 落地。复用公共数据层 app.db.auth
（多方言 + 项目 db 框架），所有写操作经命名参数，杜绝注入；表名/列名固定不来自输入。

路由前缀：/api/v1/auth/manage
  GET    /users                  列出全部用户（不含密码）
  POST   /users                  创建用户 {bk_user_name, bk_password, bk_role?, bk_supplier_account?}
  GET    /policies               列出策略（?principal=&obj_id=&action=&res_type=&supplier=）
  POST   /policies               授予单条策略 {principal, obj_id, action, res_type?, supplier?, effect?}
  DELETE /policies               撤销策略（{id} 或 {principal, obj_id, action, supplier?}）
  POST   /policies/batch         批量授权：{scenario, principal, models?[], model?} 或 {items:[...]}
"""

import logging

from flask import Blueprint, jsonify, request

from app.config.settings import get_config
from app.db.auth import (
    ROLE_ADMIN, ROLE_NORMAL,
    list_users as db_list_users,
    create_user as db_create_user,
    exists_user as db_exists_user,
    list_policies as db_list_policies,
    grant_policy as db_grant_policy,
    revoke_policy as db_revoke_policy,
    revoke_all_for_user as db_revoke_all_for_user,
    grant_batch as db_grant_batch,
    resolve_scenario as db_resolve_scenario,
    VALID_ACTIONS,
    RES_TYPE_MODEL_INSTANCE,
    EFFECT_ALLOW,
)

logger = logging.getLogger('api.auth_manage')

auth_manage_bp = Blueprint('auth_manage', __name__)


# ---------------------------------------------------------------------------
# 响应封装（与原项目 BaseResp 一致）
# ---------------------------------------------------------------------------
def _ok(data=None, message=''):
    return jsonify({
        'result': True,
        'bk_error_code': 0,
        'bk_error_msg': message,
        'data': data if data is not None else {},
    }), 200


def _fail(message, code=1199999):
    return jsonify({
        'result': False,
        'bk_error_code': code,
        'bk_error_msg': message,
    }), 200


def _require_admin():
    """管理接口最小保护：开启鉴权时要求超管（bk_role==1）。

    ENABLE_AUTH=False（默认）时全站短路放行，管理接口同样放开，便于本地运维。
    开启后必须有有效 token 且为超管，否则返回 1302102。
    """
    cfg = get_config()
    if not cfg.ENABLE_AUTH:
        return None
    from app.auth.identity import current_user_payload
    payload = current_user_payload()
    if not payload or payload.get('bk_role') != ROLE_ADMIN:
        return _fail('无操作权限（管理接口需超管）', cfg.AUTH_ERR_NO_PERMISSION)
    return None


# ---------------------------------------------------------------------------
# 用户
# ---------------------------------------------------------------------------
@auth_manage_bp.route('/users', methods=['GET'])
def get_users():
    guard = _require_admin()
    if guard:
        return guard
    try:
        users = db_list_users()
        # 剥离密码列（db_list_users 已不含，这里双保险）
        safe = [{k: v for k, v in u.items() if k != 'bk_password'} for u in users]
        return _ok({'count': len(safe), 'users': safe})
    except Exception as e:
        logger.error(f'列出用户失败: {e}')
        return _fail(f'列出用户失败: {e}')


@auth_manage_bp.route('/users', methods=['POST'])
def create_user():
    guard = _require_admin()
    if guard:
        return guard
    try:
        body = request.get_json(silent=True) or {}
        name = (body.get('bk_user_name') or '').strip()
        password = body.get('bk_password') or ''
        role = body.get('bk_role', ROLE_NORMAL)
        supplier = body.get('bk_supplier_account') or None
        if not name:
            return _fail('用户名不能为空（bk_user_name 必填）', cfg_err_param())
        if len(password) < 6:
            return _fail('密码长度至少 6 位', cfg_err_param())
        if role not in (ROLE_ADMIN, ROLE_NORMAL):
            return _fail('非法角色值（仅 1=超管 / 2=普通用户）', cfg_err_param())
        if db_exists_user(name):
            return _fail(f'用户已存在: {name}', cfg_err_param())
        user = db_create_user(name=name, password=password, role=role, supplier=supplier)
        safe = {k: v for k, v in user.items() if k != 'bk_password'}
        return _ok(safe, f'用户 {name} 创建成功')
    except ValueError as e:
        return _fail(str(e), cfg_err_param())
    except Exception as e:
        logger.error(f'创建用户失败: {e}')
        return _fail(f'创建用户失败: {e}')


# ---------------------------------------------------------------------------
# 策略
# ---------------------------------------------------------------------------
@auth_manage_bp.route('/policies', methods=['GET'])
def list_policies():
    guard = _require_admin()
    if guard:
        return guard
    try:
        principal = request.args.get('principal') or None
        obj_id = request.args.get('obj_id') or None
        action = request.args.get('action') or None
        res_type = request.args.get('res_type') or None
        supplier = request.args.get('supplier') or None
        business_id = request.args.get('business_id') or None
        rows = db_list_policies(supplier=supplier, principal=principal,
                                res_type=res_type, obj_id=obj_id, action=action,
                                business_id=business_id)
        return _ok({'count': len(rows), 'policies': rows})
    except Exception as e:
        logger.error(f'列出策略失败: {e}')
        return _fail(f'列出策略失败: {e}')


@auth_manage_bp.route('/policies', methods=['POST'])
def grant_policy():
    guard = _require_admin()
    if guard:
        return guard
    try:
        body = request.get_json(silent=True) or {}
        principal = (body.get('principal') or '').strip()
        obj_id = body.get('obj_id')  # None → 类级（全部模型）
        action = (body.get('action') or '').strip().lower()
        res_type = body.get('res_type') or RES_TYPE_MODEL_INSTANCE
        supplier = body.get('supplier') or get_config().DEFAULT_SUPPLIER
        effect = body.get('effect') or EFFECT_ALLOW
        business_id = body.get('business_id')
        if not principal:
            return _fail('principal（用户名）必填', cfg_err_param())
        if not db_exists_user(principal):
            return _fail(f'用户不存在: {principal}', cfg_err_param())
        if action not in VALID_ACTIONS:
            return _fail(f'非法动作: {action}（仅 {VALID_ACTIONS}）', cfg_err_param())
        result = db_grant_policy(supplier=supplier, principal=principal,
                                 res_type=res_type, obj_id=obj_id,
                                 action=action, business_id=business_id, effect=effect)
        if result['skipped']:
            return _ok(result['policy'], f'策略已存在（跳过）：{action}@{obj_id}')
        return _ok(result['policy'], f'授权成功：{action}@{obj_id or "全部模型"}')
    except ValueError as e:
        return _fail(str(e), cfg_err_param())
    except Exception as e:
        logger.error(f'授权失败: {e}')
        return _fail(f'授权失败: {e}')


@auth_manage_bp.route('/policies', methods=['DELETE'])
def revoke_policy():
    guard = _require_admin()
    if guard:
        return guard
    try:
        body = request.get_json(silent=True) or {}
        policy_id = body.get('id')
        principal = (body.get('principal') or '').strip() or None
        obj_id = body.get('obj_id')
        action = (body.get('action') or '').strip().lower() or None
        supplier = body.get('supplier') or None
        business_id = body.get('business_id')
        if policy_id is not None:
            n = db_revoke_policy(policy_id=policy_id)
        else:
            if not (principal and action):
                return _fail('撤销需提供 id，或 (principal + action)；obj_id 可省略（类级=全部模型）', cfg_err_param())
            if action not in VALID_ACTIONS:
                return _fail(f'非法动作: {action}', cfg_err_param())
            n = db_revoke_policy(supplier=supplier, principal=principal,
                                 obj_id=obj_id, action=action, business_id=business_id)
        return _ok({'deleted': n}, f'已撤销 {n} 条策略')
    except ValueError as e:
        return _fail(str(e), cfg_err_param())
    except Exception as e:
        logger.error(f'撤销策略失败: {e}')
        return _fail(f'撤销策略失败: {e}')


@auth_manage_bp.route('/policies/batch', methods=['POST'])
def batch_grant():
    guard = _require_admin()
    if guard:
        return guard
    try:
        body = request.get_json(silent=True) or {}
        principal = (body.get('principal') or '').strip()
        if not principal:
            return _fail('principal（用户名）必填', cfg_err_param())
        if not db_exists_user(principal):
            return _fail(f'用户不存在: {principal}', cfg_err_param())

        # 方式一：显式 items 列表
        items = body.get('items')
        if items:
            # 补全默认值 + 校验
            norm = []
            for it in items:
                a = (it.get('action') or '').strip().lower()
                if a not in VALID_ACTIONS:
                    return _fail(f'非法动作: {a}', cfg_err_param())
                norm.append({
                    'supplier': it.get('supplier') or get_config().DEFAULT_SUPPLIER,
                    'principal': principal,
                    'res_type': it.get('res_type') or RES_TYPE_MODEL_INSTANCE,
                    'obj_id': it.get('obj_id'),
                    'action': a,
                    'business_id': it.get('business_id'),
                    'effect': it.get('effect') or EFFECT_ALLOW,
                })
            stats = db_grant_batch(norm)
            return _ok(stats, f'批量授权完成：新增 {stats["granted"]} / 跳过 {stats["skipped"]} / 失败 {stats["failed"]}')

        # 方式二：按场景
        scenario = (body.get('scenario') or '').strip()
        if not scenario:
            return _fail('需提供 items（显式列表）或 scenario（场景名）', cfg_err_param())
        models = body.get('models') or None
        model = body.get('model') or None
        business_id = body.get('business_id')
        if isinstance(models, str):
            models = [m.strip() for m in models.split(',') if m.strip()]
        try:
            items = db_resolve_scenario(scenario, principal,
                                       models=models, model=model,
                                       business_id=business_id)
        except ValueError as e:
            return _fail(str(e), cfg_err_param())
        stats = db_grant_batch(items)
        return _ok({'scenario': scenario, 'items': len(items), **stats},
                   f'场景[{scenario}] 批量授权完成：新增 {stats["granted"]} / 跳过 {stats["skipped"]} / 失败 {stats["failed"]}')
    except ValueError as e:
        return _fail(str(e), cfg_err_param())
    except Exception as e:
        logger.error(f'批量授权失败: {e}')
        return _fail(f'批量授权失败: {e}')


def cfg_err_param():
    """参数错误码（沿用通用错误码 1199999）。"""
    return 1199999
