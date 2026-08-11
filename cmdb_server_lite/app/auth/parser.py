"""
路由 + Method → ResourceAttribute[]（对齐上游 ac/parser.ParseAttribute）

【动作模型严格对齐上游】
上游 src/ac/iam/adaptor.go ConvertSysInstanceActionID 对「模型实例」只认 4 个动作：
    meta.Create → Create      meta.Update → Edit
    meta.Delete → Delete      meta.Find   → View
其余（含 UpdateMany / DeleteMany）一律返回 Unsupported 并报错；
上游更不存在 unassociate 这种动作。因此 parser 只产出上述 4 个基础动作。

【批量端点逐实例展开】
对齐上游 topolatest.go:1185-1194——批量删除从 body 取 delete.inst_ids，
为每个实例生成一个独立的 meta.Delete 资源，而非一个 obj 级的 deleteMany 资源。
lite 同理：批量删除/更新在此展开为多个单动作资源，与 handler 层
check_instances / pre_authorize_update 的逐实例语义保持一致。

覆盖范围：
  POST   /api/v1/models/<m>/instances        → (modelInstance, create)
  GET    /api/v1/models/<m>/instances*       → (modelInstance, find)    → 读默认放行
  PUT    /api/v1/models/<m>/instances/<id>   → (modelInstance, update, id)
  PUT    /api/v1/models/<m>/instances        → 逐实例展开 (modelInstance, update, id_i)
  DELETE /api/v1/models/<m>/instances/<id>   → (modelInstance, delete, id)
  DELETE /api/v1/models/<m>/instances        → 逐实例展开 (modelInstance, delete, id_i)

  DELETE /delete/instassociation/<obj_id>/<id>
      → 查关联记录，对【关联双方模型】各生成 (modelInstance, update, inst_id)
        对齐上游 topolatest.go:735-799（searchModels(bk_obj_id IN [ObjectID, AsstObjectID])
        + generateUpdateInstanceResource）。取消关联在上游受 Edit 权限管控，
        且双方都必须有权——避免从对端侧绕过受保护模型的限制。

其余路由（auth/login、health、模型元数据、关联分表等）返回 None，
before_request 不拦截——保证非实例端点零回归。
"""

import re
from app.auth.resource import Action, ResourceType, ResourceAttribute

# 仅匹配 /api/v1/models/<m>/instances 及其单实例子路径；
# /instances/search、/instances/check-unique、/instances/count 等多段路径不匹配。
INSTANCE_RE = re.compile(r'^/api/v1/models/([^/]+)/instances(?:/([^/]+))?$')

# 取消关联（删除实例关联）端点。
UNASSOC_RE = re.compile(r'^/delete/instassociation/([^/]+)/([^/]+)$')


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _json_body(request):
    """安全读取 JSON body。

    before_request 阶段读取会被 Flask 缓存，后续 handler 再次 get_json 不受影响。
    """
    try:
        return request.get_json(silent=True) or {}
    except Exception:
        return {}


def _delete_ids(request):
    """批量删除端点的实例 ID（对齐上游 getValueFromBody("delete.inst_ids")）。

    lite 删除端点约定 body 为 {"ids": [...]}。
    """
    data = _json_body(request)
    raw = data.get('ids') or data.get('bk_inst_ids') or []
    if not isinstance(raw, (list, tuple)):
        return []
    return [i for i in (_to_int(x) for x in raw) if i is not None]


def _update_ids(request):
    """批量更新端点的实例 ID，兼容 lite 的两种 body 形态：

    形态一 {"update": [{"inst_id": .., "datas": {..}}, ..]}
    形态二 {"ids": [..], "data": {..}}
    """
    data = _json_body(request)
    if isinstance(data.get('update'), list):
        raw = [item.get('inst_id') for item in data['update']
               if isinstance(item, dict)]
    else:
        raw = data.get('ids') or []
    if not isinstance(raw, (list, tuple)):
        return []
    return [i for i in (_to_int(x) for x in raw) if i is not None]


def _lookup_association(url_obj_id, asst_id):
    """按 association_id 查关联记录（对齐上游 ps.getInstAssociation(objID, {id: assoID})）。

    关联记录在源/目标两个分表各存一份，因此用 URL 携带的 obj_id 定位分表即可命中。
    查不到返回 None。
    """
    aid = _to_int(asst_id)
    if aid is None:
        return None
    try:
        from app.service.association_service import get_inst_asst_table_name
        from app.db.executor import query_one
        table = get_inst_asst_table_name(url_obj_id)
        return query_one(
            f'SELECT bk_obj_id, bk_asst_obj_id, bk_inst_id, bk_asst_inst_id '
            f'FROM "{table}" WHERE id = :aid',
            {'aid': aid})
    except Exception:
        return None


def _parse_unassociate(url_obj_id, asst_id):
    """取消关联 → 关联双方模型各一个 update 资源（上游语义）。"""
    rec = _lookup_association(url_obj_id, asst_id)
    if not rec:
        # 关联记录不存在：删除本身即 no-op。回退为 URL 侧单资源，
        # 不放宽既有约束（fail-safe，不 fail-open）。
        return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE,
                                  obj_id=url_obj_id)]

    src_obj = rec.get('bk_obj_id')
    dst_obj = rec.get('bk_asst_obj_id')
    src_inst = _to_int(rec.get('bk_inst_id'))
    dst_inst = _to_int(rec.get('bk_asst_inst_id'))

    # 模型自关联：上游 len(models)==1 分支，对两个实例各生成一个 update 资源
    if src_obj == dst_obj:
        return [
            ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE,
                              obj_id=src_obj, instance_id=src_inst),
            ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE,
                              obj_id=src_obj, instance_id=dst_inst),
        ]

    # 跨模型关联：双方模型各一个，任一侧无权即整体拒绝
    return [
        ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE,
                          obj_id=src_obj, instance_id=src_inst),
        ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE,
                          obj_id=dst_obj, instance_id=dst_inst),
    ]


def parse_route(request):
    path = request.path
    method = request.method

    m = INSTANCE_RE.match(path)
    if m:
        model_id = m.group(1)
        instance_id = m.group(2)

        if method == 'POST':
            return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.CREATE,
                                      obj_id=model_id)]

        if method == 'GET':
            return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.FIND,
                                      obj_id=model_id)]

        if method == 'PUT':
            if instance_id:
                return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE,
                                          obj_id=model_id,
                                          instance_id=_to_int(instance_id))]
            ids = _update_ids(request)
            if ids:
                return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE,
                                          obj_id=model_id, instance_id=i) for i in ids]
            # body 未携带 ID：退化为模型级 update 资源
            return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE,
                                      obj_id=model_id)]

        if method == 'DELETE':
            if instance_id:
                return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.DELETE,
                                          obj_id=model_id,
                                          instance_id=_to_int(instance_id))]
            ids = _delete_ids(request)
            if ids:
                return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.DELETE,
                                          obj_id=model_id, instance_id=i) for i in ids]
            # body 未携带 ID：退化为模型级 delete 资源
            return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.DELETE,
                                      obj_id=model_id)]
        return None

    # 取消关联：必须放在 INSTANCE 分支之外，否则非实例路径会在上方提前 return None
    um = UNASSOC_RE.match(path)
    if um and method == 'DELETE':
        return _parse_unassociate(um.group(1), um.group(2))

    return None
