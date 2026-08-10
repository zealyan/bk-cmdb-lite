"""
路由 + Method → ResourceAttribute[]（轻量版上游 ac/parser.ParseAttribute）

lite 路由是干净的 REST，无需上游的正则引擎，用「路由表 + Method」即可。

覆盖范围（实例端点）：
  POST   /api/v1/models/<m>/instances            → (modelInstance, create)
  PUT    /api/v1/models/<m>/instances/<id>       → (modelInstance, update,  instance_id)
  PUT    /api/v1/models/<m>/instances            → (modelInstance, updateMany)
  DELETE /api/v1/models/<m>/instances            → (modelInstance, deleteMany)
  GET    /api/v1/models/<m>/instances*           → (modelInstance, find)  → 读默认放行

其余路由（auth/login、health、模型元数据、关联分表等）返回 None，
before_request 不拦截——保证非实例端点零回归。
"""

import re
from app.auth.resource import Action, ResourceType, ResourceAttribute

# 仅匹配 /api/v1/models/<m>/instances 及其单实例子路径；
# /instances/search、/instances/check-unique、/instances/count 等多段路径不匹配。
INSTANCE_RE = re.compile(r'^/api/v1/models/([^/]+)/instances(?:/([^/]+))?$')


def parse_route(request):
    path = request.path
    method = request.method
    m = INSTANCE_RE.match(path)
    if not m:
        return None
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
    return None
