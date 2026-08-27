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
  GET    /api/v1/models/<m>/instances        → (modelInstance, find)    → 读默认放行
  GET    /api/v1/models/<m>/instances/<id>   → (modelInstance, find, id) → 读默认放行
  PUT    /api/v1/models/<m>/instances/<id>   → (modelInstance, update, id)
  PUT    /api/v1/models/<m>/instances        → 逐实例展开 (modelInstance, update, id_i)
  DELETE /api/v1/models/<m>/instances/<id>   → (modelInstance, delete, id)
  DELETE /api/v1/models/<m>/instances        → 逐实例展开 (modelInstance, delete, id_i)

  # 业务拓扑（biz/set/module/transfer）
  # 上游：集群(set)/模块(module)/主线实例在 IAM 侧统一为 biz_topology；
  # 主机转移为专用动作（lite 用 transfer 区分于主机 update）。
  # 业务隔离：biz_topology 的 business_id 维度（对应上游 ResourceAttribute.BusinessID /
  #   IAM 中 bizTopology 的 Parents=[business]）由解析器在此解析并写入 ResourceAttribute.business_id：
  #   - 创建集群：bizId 直接取自 URL /topo/biz/<bizId>/set
  #   - 创建模块：由 setId 查 cc_SetBase.bk_biz_id 反推
  #   - 编辑/删除节点：由 set/module 的 instId 查对应 Base 表反推 bk_biz_id
  #   - 主机转移：由目标 module_id 查 cc_ModuleBase.bk_biz_id 反推（主机↔模块关联
  #     的归属业务，对齐上游 host transfer 的 Parents=[business]）
  #   business_id=None 表示「全部业务」（类级），仅 business_id=NULL 的策略可放行。
  POST   /api/v1/topo/biz/<bizId>/set              → (biz_topology, create, business_id=<bizId>)   # 创建集群
  POST   /api/v1/topo/set/<setId>/module          → (biz_topology, create, business_id=<setId 反推>)  # 创建模块
  POST   /api/v1/topo/biz                         → (business, create, business_id=None)            # 创建业务（根节点，类级动作，对齐上游 CreateBusiness）
  POST   /api/v1/topo/instance/mainline           → (biz_topology, create, business_id=<body.bk_biz_id>)  # 创建主线实例（此前漏覆盖→已修复）
  PUT    /api/v1/topo/node/<objId>/<instId>        → (biz_topology, update, business_id=<反推>)   # 编辑集群/模块
  DELETE /api/v1/topo/node/<objId>/<instId>        → (biz_topology, delete, business_id=<反推>)   # 删除集群/模块
  POST   /api/v1/host/transfer/modules             → (hostInstance, transfer, business_id=<目标模块反推>)  # 主机转移（写，per-biz：业务作用域由目标模块归属反推）
  POST   /api/v1/host/transfer/modules/across/biz  → (hostInstance, transfer, business_id=<src_biz>) + (hostInstance, transfer, business_id=<dst_biz 反推>)  # 跨业务转移：源业务转出 + 目标业务转入（双业务维度）
  # 读类端点（GET /topo/*、POST /topo/statistics、POST /topo/hosts/search、
  # GET/POST /host/transfer/topology|internal|host/modules）不匹配下方正则 → 返回 None → 放行

  # 以下为读操作子路径，不匹配 INSTANCE_RE（尾段非数字），parse_route 返回 None → 不拦截：
  #   POST/GET /api/v1/models/<m>/instances/search      （列表搜索，页面加载即用此端点）
  #   POST    /api/v1/models/<m>/instances/check-unique
  #   POST    /api/v1/models/<m>/instances/check-associations
  #   POST    /api/v1/models/instances/count

  DELETE /delete/instassociation/<obj_id>/<id>
      → 查关联记录，对【关联双方模型】各生成 (modelInstance, update, inst_id)
        对齐上游 topolatest.go:735-799（searchModels(bk_obj_id IN [ObjectID, AsstObjectID])
        + generateUpdateInstanceResource）。取消关联在上游受 Edit 权限管控，
        且双方都必须有权——避免从对端侧绕过受保护模型的限制。

  POST /create/instassociation
      → 读 body 的 bk_obj_id/bk_asst_obj_id（含 bk_inst_id/bk_asst_inst_id），
        对【关联双方模型】各生成 (modelInstance, update, inst_id)
        对齐上游：新增关联=实例编辑，同样受 Edit 权限管控（与取消关联对称，
        任一侧无权即整体拒绝，避免从对端侧绕过受保护模型的限制）。

其余路由（auth/login、health、模型元数据、关联分表等）返回 None，
before_request 不拦截——保证非实例端点零回归。
"""

import re
from app.auth.resource import Action, ResourceType, ResourceAttribute
from app.db.executor import query_one, query_all

# 仅匹配 /api/v1/models/<m>/instances（列表）及其【数字 ID】单实例子路径；
# 尾段必须是纯数字的实例 ID，否则不匹配（parse_route 返回 None → before_request 不拦截）。
# 因此 /instances/search、/instances/check-unique、/instances/check-associations、
# /instances/count 等读操作子路径不会被误判为 create/update/delete（此前 (?:/([^/]+))?
# 会把 /search 当成 instance_id，导致 POST /instances/search 被错误归类为 CREATE）。
INSTANCE_RE = re.compile(r'^/api/v1/models/([^/]+)/instances(?:/(\d+))?$')

# 取消关联（删除实例关联）端点。
UNASSOC_RE = re.compile(r'^/delete/instassociation/([^/]+)/([^/]+)$')

# 新增关联（创建实例关联）端点。上游语义：新增关联=实例编辑，受 Edit 权限管控；
# 与取消关联对称，对关联双方模型各生成一个 update 资源（任一侧无权即整体拒绝）。
CREATE_ASSOC_RE = re.compile(r'^/create/instassociation$')

# ───────────────────────────────────────────────────────────
# 业务拓扑（biz / set / module / transfer）路由
# 上游：集群(set)/模块(module)/主线实例在 IAM 侧统一为资源类型 biz_topology，
# 动作复用 create/edit/delete（CMDB 内部 Update → IAM edit_*）；
# 主机转移是专用动作（lite 用 transfer 区分于主机 update）。
# 读类端点（GET /topo/*、POST /topo/statistics、POST /topo/hosts/search、
# GET/POST /host/transfer/topology|internal|host/modules）不匹配下列正则，
# 由 before_request 放行（find 默认允许）。
# ───────────────────────────────────────────────────────────

# 创建集群：POST /api/v1/topo/biz/<bizId>/set
TOPO_SET_CREATE_RE = re.compile(r'^/api/v1/topo/biz/([^/]+)/set$')
# 创建模块：POST /api/v1/topo/set/<setId>/module
TOPO_MODULE_CREATE_RE = re.compile(r'^/api/v1/topo/set/([^/]+)/module$')
# 创建 topo 实例（主线实例）：POST /api/v1/topo/instance/mainline
#   bizId 取自请求体 bk_biz_id（与 create_mainline_instance handler 一致：data.get('bk_biz_id')）
TOPO_MAINLINE_CREATE_RE = re.compile(r'^/api/v1/topo/instance/mainline$')
# 创建业务（根节点，业务尚未存在，无具体 business_id）：POST /api/v1/topo/biz
#   对齐上游 CreateBusiness：business 资源类级动作（business_id=None）；
#   admin 全权放行，非 admin 需类级 business:create 策略，否则 fail-closed。
TOPO_BIZ_CREATE_RE = re.compile(r'^/api/v1/topo/biz$')
# 编辑/删除集群或模块：PUT|DELETE /api/v1/topo/node/<objId>/<instId>
#   objId ∈ {set, module}（及任意主线 obj）；统一映射为 biz_topology 资源
TOPO_NODE_RE = re.compile(r'^/api/v1/topo/node/([^/]+)/([^/]+)$')
# 主机转移（写）：POST /api/v1/host/transfer/modules
TRANSFER_RE = re.compile(r'^/api/v1/host/transfer/modules$')
# 跨业务转移（写）：POST /api/v1/host/transfer/modules/across/biz
TRANSFER_ACROSS_RE = re.compile(r'^/api/v1/host/transfer/modules/across/biz$')


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _resolve_topo_biz(obj_id, inst_id):
    """反推拓扑节点的业务 ID（用于 per-biz 授权，对齐上游 bizTopology 以 business 为父级作用域）。

    - obj_id == 'set'    → cc_SetBase.bk_biz_id（inst_id 为 bk_set_id）
    - obj_id == 'module' → cc_ModuleBase.bk_biz_id（inst_id 为 bk_module_id）
    - 其他主线对象（lite 未暴露其写路由）→ 返回 None，退化为类级（仅 business_id=NULL 策略可放行）
    查不到 / inst_id 非法 → 返回 None（fail-safe，不放宽约束）。
    返回统一为字符串，与 CLI / 策略存储的 business_id 类型一致（VARCHAR）。
    """
    if inst_id is None:
        return None
    if obj_id == 'set':
        row = query_one('SELECT bk_biz_id FROM cc_SetBase WHERE bk_set_id = :i', {'i': inst_id})
    elif obj_id == 'module':
        row = query_one('SELECT bk_biz_id FROM cc_ModuleBase WHERE bk_module_id = :i', {'i': inst_id})
    else:
        return None
    if not row:
        return None
    biz = row.get('bk_biz_id')
    return str(biz) if biz is not None else None


def _resolve_transfer_biz(module_ids, fallback_biz_id=None):
    """反推主机转移目标模块所属业务 ID（用于 per-biz 授权，对齐上游 host transfer 的 Parents=[business]）。

    主机转移的本质是在 cc_ModuleHostConfig 上建立/改绑 主机↔模块 关联，
    目标模块的业务归属即本次操作的业务作用域。服务层已校验所有目标模块同属一个
    业务（transfer_modules 会拒绝跨业务的模块），故取其一致的 bk_biz_id；
    若该集为空 / 跨业务 / 查不到 → 退化为 fallback（通常来自请求体 bk_biz_id），
    再不行则 None（fail-safe，仅 business_id=NULL 的类级策略可放行）。

    Args:
        module_ids:     目标模块 ID 列表（来自请求体 module_id）
        fallback_biz_id: 退化用的业务 ID（来自请求体 bk_biz_id），可选
    """
    biz = None
    if module_ids:
        try:
            placeholders = ', '.join([f':mid_{i}' for i in range(len(module_ids))])
            params = {f'mid_{i}': mid for i, mid in enumerate(module_ids)}
            rows = query_all(
                f'SELECT DISTINCT bk_biz_id FROM cc_ModuleBase '
                f'WHERE bk_module_id IN ({placeholders})',
                params)
            bizs = {r.get('bk_biz_id') for r in rows if r.get('bk_biz_id') is not None}
            if len(bizs) == 1:
                biz = str(next(iter(bizs)))
        except Exception:
            biz = None
    if biz is None and fallback_biz_id is not None:
        biz = str(fallback_biz_id)
    return biz


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


def _parse_associate(request):
    """新增关联 → 关联双方模型各一个 update 资源（对齐上游：新增关联=实例编辑，受 Edit 权限管控）。

    与 _parse_unassociate 对称，但创建关联时关联记录尚未写入，故直接读请求体
    （bk_obj_id / bk_asst_obj_id / bk_inst_id / bk_asst_inst_id）得到关联双方模型与实例，
    不再查 DB。
    """
    body = request.get_json(silent=True) or {}
    src_obj = (body.get('bk_obj_id') or '').strip()
    dst_obj = (body.get('bk_asst_obj_id') or '').strip()
    src_inst = _to_int(body.get('bk_inst_id'))
    dst_inst = _to_int(body.get('bk_asst_inst_id'))

    if not src_obj and not dst_obj:
        # 请求体未携带模型信息：fail-safe，回退为默认模型级 update（不放宽约束）
        return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE,
                                  obj_id=src_obj or dst_obj)]

    # 模型自关联：对两个实例各生成一个 update 资源
    if src_obj == dst_obj:
        items = []
        if src_inst is not None:
            items.append(ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE,
                                            obj_id=src_obj, instance_id=src_inst))
        if dst_inst is not None and dst_inst != src_inst:
            items.append(ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE,
                                            obj_id=src_obj, instance_id=dst_inst))
        if not items:
            items.append(ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE,
                                            obj_id=src_obj))
        return items

    # 跨模型关联：双方模型各一个 update 资源，任一侧无权即整体拒绝
    items = [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE,
                               obj_id=src_obj, instance_id=src_inst)]
    if dst_obj:
        items.append(ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE,
                                       obj_id=dst_obj, instance_id=dst_inst))
    return items


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

    # ── 业务拓扑：集群/模块 创建 ──
    # 创建集群：POST /api/v1/topo/biz/<bizId>/set —— bizId 直接取自 URL
    ts = TOPO_SET_CREATE_RE.match(path)
    if ts and method == 'POST':
        biz_id = _to_int(ts.group(1))
        return [ResourceAttribute(ResourceType.BIZ_TOPOLOGY, Action.CREATE,
                                  obj_id=ResourceType.BIZ_TOPOLOGY,
                                  business_id=str(biz_id) if biz_id is not None else None)]
    # 创建模块：POST /api/v1/topo/set/<setId>/module —— 由 setId 反推 biz
    tm = TOPO_MODULE_CREATE_RE.match(path)
    if tm and method == 'POST':
        set_id = _to_int(tm.group(1))
        biz_id = _resolve_topo_biz('set', set_id)
        return [ResourceAttribute(ResourceType.BIZ_TOPOLOGY, Action.CREATE,
                                  obj_id=ResourceType.BIZ_TOPOLOGY, business_id=biz_id)]
    # 创建 topo 实例（主线实例）：POST /api/v1/topo/instance/mainline
    #   bizId 取自请求体 bk_biz_id（与 create_mainline_instance handler 一致：data.get('bk_biz_id')）；
    #   前端「创建 topo 实例」调用此路由，此前未覆盖 → parse_route 返回 None → 绕过鉴权（fail-open）；
    #   现补上 business_id 隔离：未带/非法 bk_biz_id 时 business_id=None，仅 business_id=NULL 的类级策略可放行
    #   （fail-closed，tom 无类级策略 → 拒绝）；GET /topo/instance/mainline（读拓扑树）method!=POST 不命中 → 仍放行（读默认允许）。
    tml = TOPO_MAINLINE_CREATE_RE.match(path)
    if tml and method == 'POST':
        body = _json_body(request)
        biz_id = _to_int(body.get('bk_biz_id'))
        return [ResourceAttribute(ResourceType.BIZ_TOPOLOGY, Action.CREATE,
                                  obj_id=ResourceType.BIZ_TOPOLOGY,
                                  business_id=str(biz_id) if biz_id is not None else None)]
    # 创建业务：POST /api/v1/topo/biz —— 类级动作，business_id=None（业务尚未存在）
    #   对齐上游 CreateBusiness：business 资源类级动作；admin 全权，非 admin 需类级策略。
    tb = TOPO_BIZ_CREATE_RE.match(path)
    if tb and method == 'POST':
        return [ResourceAttribute(ResourceType.BUSINESS, Action.CREATE,
                                  obj_id=ResourceType.BUSINESS, business_id=None)]
    # 编辑/删除集群或模块：PUT|DELETE /api/v1/topo/node/<objId>/<instId>
    tn = TOPO_NODE_RE.match(path)
    if tn and method in ('PUT', 'DELETE'):
        action = Action.UPDATE if method == 'PUT' else Action.DELETE
        # objId(set/module/主线) 不影响资源类型：上游 IAM 侧统一为 biz_topology
        obj_id = tn.group(1)
        inst_id = _to_int(tn.group(2))
        biz_id = _resolve_topo_biz(obj_id, inst_id)
        return [ResourceAttribute(ResourceType.BIZ_TOPOLOGY, action,
                                  obj_id=ResourceType.BIZ_TOPOLOGY, business_id=biz_id)]
    # 主机转移（写）：POST /api/v1/host/transfer/modules
    # 业务作用域从目标模块反推（cc_ModuleBase.bk_biz_id），对齐上游 host transfer 的
    # Parents=[business]；目标模块须同属一个业务（服务层已校验），故取一致的 bk_biz_id；
    # 请求体 bk_biz_id 作为退化来源（fail-safe），再不行则 None（仅类级策略可放行）。
    tfr = TRANSFER_RE.match(path)
    if tfr and method == 'POST':
        body = _json_body(request)
        module_ids = [i for i in (_to_int(x) for x in (body.get('module_id') or [])) if i is not None]
        fb = _to_int(body.get('bk_biz_id'))
        biz_id = _resolve_transfer_biz(module_ids, fallback_biz_id=fb)
        return [ResourceAttribute(ResourceType.HOST_INSTANCE, Action.TRANSFER,
                                  obj_id='host', business_id=biz_id)]
    # 跨业务转移（写）：POST /api/v1/host/transfer/modules/across/biz
    # 双业务维度：源业务（转出）+ 目标业务（转入）。
    # 源业务取自请求体 src_bk_biz_id；目标业务由请求体 module_id 反推
    # cc_ModuleBase.bk_biz_id（复用 _resolve_transfer_biz，目标模块须同属一个业务，
    # 否则服务层拒绝）。coarse_authorize 对多资源用 all(d.authorized) 判定；
    # admin 全权，非 admin 需源+目标业务双维度策略（当前无策略则 fail-closed）。
    tfra = TRANSFER_ACROSS_RE.match(path)
    if tfra and method == 'POST':
        body = _json_body(request)
        src = _to_int(body.get('src_bk_biz_id'))
        dst = _resolve_transfer_biz(
            [i for i in (_to_int(x) for x in (body.get('module_id') or [])) if i is not None])
        return [
            ResourceAttribute(ResourceType.HOST_INSTANCE, Action.TRANSFER,
                              obj_id='host',
                              business_id=str(src) if src is not None else None),
            ResourceAttribute(ResourceType.HOST_INSTANCE, Action.TRANSFER,
                              obj_id='host', business_id=dst),
        ]

    # 取消关联：必须放在 INSTANCE 分支之外，否则非实例路径会在上方提前 return None
    um = UNASSOC_RE.match(path)
    if um and method == 'DELETE':
        return _parse_unassociate(um.group(1), um.group(2))

    # 新增关联：必须放在 INSTANCE 分支之外；与取消关联对称，受实例 Edit 权限管控
    cmr = CREATE_ASSOC_RE.match(path)
    if cmr and method == 'POST':
        return _parse_associate(request)

    return None
