"""
鉴权后端接口 + 内置轻量实现

- Authorizer：可插拔鉴权后端接口（对应上游 ac.AuthorizeInterface）。
  未来接真实 IAM 只需新增一个 IAMAuthorizer 实现并替换 BuiltinAuthorizer，业务代码零改动。
- BuiltinAuthorizer：本地 SQLite 策略的最小实现（对应上游 IAMAuthorizer 的本地版）。

粗粒度（模型级）决策：供全局 before_request 的 auth_filter 使用。
实例级（owner）决策在 manager 层做（需要按 ID 取实例 owner，见 manager.check_instances）。
"""

from app.config.settings import get_config
from app.auth.policy import query_allow
from app.auth.resource import Action, ResourceType, ResourceAttribute


class Decision:
    """单条鉴权结论"""

    def __init__(self, authorized, reason=''):
        self.authorized = authorized
        self.reason = reason


class Authorizer:
    """可插拔鉴权后端接口"""

    def authorize(self, user, supplier, role, *resources):
        raise NotImplementedError


class BuiltinAuthorizer(Authorizer):
    """内置 RBAC：supplier 隔离 + 管理员全权 + 模型级策略（实例级 owner 判定在 manager 层）"""

    def authorize(self, user, supplier, role, *resources):
        return [self._decide_model(res, user, supplier, role) for res in resources]

    def _decide_model(self, res: ResourceAttribute, user, supplier, role):
        # 读操作默认放行（对齐上游 SkipReadAuthorization）
        if res.is_read():
            return Decision(True, 'read skip')
        # 管理员全权（bk_role == 1）
        if role == 1:
            return Decision(True, 'admin')
        # 模型级策略：updateMany/deleteMany 同时匹配 update/delete（见文档 §4.4
        # action IN ('update','updateMany')），避免批量端点被粗粒度层误拒。
        actions = [res.action]
        if res.action == Action.UPDATE_MANY:
            actions.append(Action.UPDATE)
        elif res.action == Action.DELETE_MANY:
            actions.append(Action.DELETE)
        # 模型级策略（obj_id 命中具体模型 或 NULL=该类全部）
        if query_allow(supplier, user, res.type, res.obj_id, actions):
            return Decision(True, 'model policy')
        return Decision(False, 'no model policy')
