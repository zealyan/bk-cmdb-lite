"""
路由 + Method → ResourceAttribute[]（轻量版上游 ac/parser.ParseAttribute）

lite 路由是干净的 REST，无需上游的正则引擎，用「路由表 + Method」即可。

覆盖范围（实例端点）：
  POST   /api/v1/models/<m>/instances            → (modelInstance, create)
  PUT    /api/v1/models/<m>/instances/<id>       → (modelInstance, update,  instance_id)
  PUT    /api/v1/models/<m>/instances            → (modelInstance, updateMany)
  DELETE /api/v1/models/<m>/instances            → (modelInstance, deleteMany)
  GET    /api/v1/models/<m>/instances*           → (modelInstance, find)  → 读默认放行

  DELETE /delete/instassociation/<obj_id>/<id>   → (modelInstance, unassociate, obj_id)
                                                      取消关联（删除实例关联）；此前该端点游离于 RBAC 之外，
                                                      此处补齐使「取消关联」同样受模型级策略约束。

其余路由（auth/login、health、模型元数据、关联分表等）返回 None，
before_request 不拦截——保证非实例端点零回归。
"""

import re
from app.auth.resource import Action, ResourceType, ResourceAttribute

# 仅匹配 /api/v1/models/<m>/instances 及其单实例子路径；
# /instances/search、/instances/check-unique、/instances/count 等多段路径不匹配。
INSTANCE_RE = re.compile(r'^/api/v1/models/([^/]+)/instances(?:/([^/]+))?$')

# 取消关联（删除实例关联）端点：obj_id 为关联源模型。
UNASSOC_RE = re.compile(r'^/delete/instassociation/([^/]+)/[^/]+$')


def parse_route(request):
    path = request.path
    method = request.method
    m = INSTANCE_RE.match(path)
    if m:
        model_id = m.group(1)
        instance_id = m.group(2)
        if method == 'POST':
            return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.CREATE, obj_id=model_id)]
        if method == 'PUT':
            if instance_id:
                return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE,
                                          obj_id=model_id, instance_id=int(instance_id))]
            return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UPDATE_MANY, obj_id=model_id)]
        if method == 'DELETE':
            return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.DELETE_MANY, obj_id=model_id)]
        if method == 'GET':
            return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.FIND, obj_id=model_id)]
    # 取消关联（删除实例关联）：DELETE /delete/instassociation/<obj_id>/<id>
    # obj_id 为关联源模型；补齐使「取消关联」受模型级策略约束（tom 无此策略即被拒）。
    # 注意：必须放在 INSTANCE 分支之外，否则非实例路径会在上方提前 return None。
    um = UNASSOC_RE.match(path)
    if um and method == 'DELETE':
        return [ResourceAttribute(ResourceType.MODEL_INSTANCE, Action.UNASSOCIATE, obj_id=um.group(1))]
    return None
