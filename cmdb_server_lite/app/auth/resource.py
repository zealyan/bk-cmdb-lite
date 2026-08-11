"""
鉴权资源抽象：对齐上游 bk-cmdb ac/meta

- Action：操作类型（create / update / delete / find / updateMany / deleteMany）
- ResourceType：资源类型（modelInstance / hostInstance / business / model）
- ResourceAttribute：一次鉴权请求的「资源 + 动作」描述，对应上游 ac/meta.ResourceAttribute
"""


class Action:
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    FIND = "find"
    UPDATE_MANY = "updateMany"
    DELETE_MANY = "deleteMany"
    UNASSOCIATE = "unassociate"


class ResourceType:
    MODEL_INSTANCE = "modelInstance"
    HOST_INSTANCE = "hostInstance"
    BUSINESS = "business"
    MODEL = "model"


class ResourceAttribute:
    """一次鉴权请求的资源描述（对齐上游 ac/meta.ResourceAttribute）

    - type:        ResourceType
    - action:      Action
    - obj_id:      模型 ID（如 bk_slb）；模型级作用域，与实例 ID 正交
    - instance_id: 实例 ID（可选，单实例维度）
    - supplier:    供应商账户（多租户隔离，默认 id0）
    """

    def __init__(self, type, action, obj_id=None, instance_id=None, supplier=None):
        self.type = type
        self.action = action
        self.obj_id = obj_id
        self.instance_id = instance_id
        self.supplier = supplier

    def is_read(self):
        return self.action == Action.FIND
