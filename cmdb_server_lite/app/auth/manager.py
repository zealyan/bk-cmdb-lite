"""
AuthManager：业务层鉴权入口（对齐上游 ac/extensions/base.go AuthManager）

- Enabled()：总开关，False 时全局短路放行（对应上游 enable-auth=false，零回归）。
- Authorize()：粗粒度（模型级）鉴权，供全局 before_request 的 auth_filter 使用。
- check_instances() / pre_authorize_update()：细粒度（实例级）逐实例 owner 判定，
  对应上游 AuthorizeByInstanceID → AuthorizeByInstances → batchAuthorize。

身份三元组：(user, supplier, role, authenticated)
- authenticated=False 且 ENABLE_AUTH=True 时一律拒绝（未登录不允许操作）。

实例级判定（对齐上游 AuthorizeByInstances 的逐实例 decision）：
  a. supplier 隔离：实例 bk_supplier_account != 当前 supplier → 拒绝
  b. 管理员全权：  role == 1 → 允许
  c. 创建者自管：  实例 creator == 当前 user → 允许（RegisterResourceCreatorAction）
  d. 模型级策略：  query_allow(模型级) 命中 → 允许（与 ids 正交，请求内只算一次）
"""

from app.config.settings import get_config
from app.auth.resource import Action, ResourceType, ResourceAttribute
from app.auth.authorizer import BuiltinAuthorizer
from app.auth.policy import grant_creator, query_allow
from app.service.instance_service import InstanceService

_authorizer = BuiltinAuthorizer()


# ───────────────────────────────────────────────────────────
# 总开关 & 身份
# ───────────────────────────────────────────────────────────

def is_enabled():
    return get_config().ENABLE_AUTH


def current_identity():
    """解析当前身份三元组 + 是否已认证。

    - 持有效 token：取 token 内 bk_user_name / bk_supplier_account / bk_role，authenticated=True
    - 无 token 且 SKIP_LOGIN（dev/默认）：回落默认 admin（超管），authenticated=True
    - 无 token 且 SKIP_LOGIN=false（生产登录模式）：视为匿名，authenticated=False
    """
    from app.auth.identity import current_user_payload, current_user, current_supplier
    cfg = get_config()
    payload = current_user_payload()
    if payload:
        return (payload.get('bk_user_name', cfg.DEFAULT_USER),
                payload.get('bk_supplier_account') or cfg.DEFAULT_SUPPLIER,
                payload.get('bk_role', 2),
                True)
    if cfg.SKIP_LOGIN:
        return (cfg.DEFAULT_USER, cfg.DEFAULT_SUPPLIER, 1, True)
    return (current_user(), current_supplier(), 2, False)


# ───────────────────────────────────────────────────────────
# 粗粒度（模型级）：供全局 auth_filter
# ───────────────────────────────────────────────────────────

def coarse_authorize(resources):
    """网关层鉴权。返回 (permission_or_None, ok)

    parser 已对齐上游把批量端点逐实例展开，资源普遍携带 instance_id。
    因此判定分两路（对齐上游 AuthorizeByInstances 的逐实例 decision）：

    - 带 instance_id：下沉到实例级判定 check_instances
      （supplier 隔离 → 创建者自管 → 模型级策略），使「创建者自管」
      在网关层即可生效，无需再向 cc_AuthPolicy 写模型级 allow。
    - 不带 instance_id：退化为模型级策略判定。

    任一资源无权 → 整体拒绝（对齐上游 GetPermissionToApply 的整体语义）。
    """
    if not is_enabled():
        return None, True
    # 读操作默认放行（对齐上游 SkipReadAuthorization），与是否认证无关
    if all(r.is_read() for r in resources):
        return None, True
    user, supplier, role, authenticated = current_identity()
    if not authenticated:
        return permission_to_apply(resources, supplier), False
    if role == 1:
        return None, True  # 管理员全权

    identity = (user, supplier, role, authenticated)

    # 按 (模型, 动作) 归并带实例 ID 的资源，逐组做实例级判定
    grouped = {}
    model_level = []
    for r in resources:
        if r.instance_id is not None:
            grouped.setdefault((r.obj_id, r.action), []).append(r.instance_id)
        else:
            model_level.append(r)

    for (obj_id, action), ids in grouped.items():
        if check_instances(obj_id, ids, action, identity):
            return permission_to_apply(resources, supplier), False

    if model_level:
        decisions = _authorizer.authorize(user, supplier, role, *model_level)
        if not all(d.authorized for d in decisions):
            return permission_to_apply(resources, supplier), False

    return None, True


# ───────────────────────────────────────────────────────────
# 细粒度（实例级）：供 handler 埋点
# ───────────────────────────────────────────────────────────

def check_instances(model_id, ids, action, identity=None):
    """逐实例 owner 判定。返回无权实例 ID 列表（空=全通过）。

    ids 仅用于按 ID 取 owner；obj_id(=model_id) 用于模型级策略——两者正交（见文档 §4 边界澄清）。
    """
    if not is_enabled():
        return []
    user, supplier, role, authenticated = identity or current_identity()
    if not authenticated:
        return list(ids)  # 未认证：全部拒绝
    if role == 1:
        return []  # 管理员全权
    if not ids:
        return []
    rows = InstanceService.get_instances_by_ids(model_id, ids)
    model_allow = query_allow(supplier, user, ResourceType.MODEL_INSTANCE, model_id, action)
    id_field = InstanceService._get_id_field(model_id)
    deny = []
    for inst in rows:
        inst_supplier = inst.get('bk_supplier_account')
        inst_creator = inst.get('creator')
        if inst_supplier is not None and inst_supplier != supplier:
            deny.append(inst[id_field]); continue          # a. supplier 隔离
        if inst_creator == user:
            continue                                         # c. 创建者自管
        if model_allow:
            continue                                         # d. 模型级策略
        deny.append(inst[id_field])                         # 以上皆否 → 无权
    return deny


def pre_authorize_update(model_id, ids, identity=None):
    """批量更新预校验（文档 §4.2-4.4）。返回 (allowed_ids, deny_ids, permission_or_None)。

    任一实例无权 → 整体拒绝且不执行任何 UPDATE（对齐上游 GetPermissionToApply）。
    """
    if not is_enabled():
        return list(ids), [], None
    deny = check_instances(model_id, ids, Action.UPDATE, identity)
    if deny:
        permission = permission_for_instances(model_id, ids, Action.UPDATE, deny, identity)
        return [i for i in ids if i not in deny], deny, permission
    return list(ids), [], None


def on_instance_created(model_id, identity=None):
    """实例创建成功后的「创建者自动授权」（对齐上游 RegisterResourceCreatorAction）。

    上游该机制是【实例级】的：把新建实例注册到 IAM，创建者仅对「该实例」获得
    Edit/Delete/Find。lite 的等价物是实例表的 creator 列（写入时打标）+
    manager.check_instances 的创建者分支——已在写入路径完成，此处无需再做。

    历史实现曾在此调用 grant_creator 写【模型级】allow，这会造成权限放大：
    创建一个实例即获得该模型下【全部实例】的 update/delete 权，可绕过针对
    该模型的权限收紧。cc_AuthPolicy 无 instance_id 列，无法表达实例级授权，
    故不再写策略行，改由 creator 列承担（网关层已在 coarse_authorize 下沉判定）。
    """
    return


# ───────────────────────────────────────────────────────────
# 无权限响应体（对齐上游 GetPermissionToApply）
# ───────────────────────────────────────────────────────────

def permission_to_apply(resources, supplier=None):
    """粗粒度（模型级）响应体"""
    if supplier is None:
        supplier = current_identity()[1]
    perms = [{
        'type': r.type,
        'action': r.action,
        'obj_id': r.obj_id,
        'instance_id': r.instance_id,
        'supplier': supplier,
    } for r in resources]
    return {'permissions': perms}


def permission_for_instances(model_id, ids, action, deny_ids, identity=None):
    """细粒度（实例级）响应体。obj_id=模型级作用域，instance_ids=被拒数据行，两者正交。"""
    supplier = (identity or current_identity())[1]
    return {
        'permissions': [{
            'type': ResourceType.MODEL_INSTANCE,
            'action': action,
            'obj_id': model_id,
            'instance_ids': deny_ids,
            'supplier': supplier,
        }]
    }
