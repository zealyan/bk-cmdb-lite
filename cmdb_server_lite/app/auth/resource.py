"""
鉴权资源抽象：对齐上游 bk-cmdb ac/meta

- Action：操作类型，常量集对齐上游 ac/meta.Action
- ResourceType：资源类型（modelInstance / hostInstance / business / bizTopology / model）
- ResourceAttribute：一次鉴权请求的「资源 + 动作」描述，对应上游 ac/meta.ResourceAttribute

【模型实例的有效动作只有 4 个】
上游 ac/iam/adaptor.go ConvertSysInstanceActionID 对模型实例仅支持
    create → Create   update → Edit   delete → Delete   find → View
UPDATE_MANY / DELETE_MANY 虽在上游 meta.Action 中有定义，但对模型实例会被判为
Unsupported；上游在 parser 层就把批量端点逐实例展开成单动作资源。
lite 与之对齐：parser 不再产出 many 动作，此处保留常量仅为兼容历史策略数据。
上游不存在 unassociate 动作——取消关联受 update(Edit) 管控（见 auth/parser.py）。

【业务拓扑动作（biz/set/module/transfer）】
- 集群(set) / 模块(module) / 主线实例在上游 IAM 侧统一映射为资源类型 biz_topology，
  动作复用 create/edit/delete（CMDB 内部 Update 映射为 IAM 的 edit_*）；
  上游无「删除业务」动作，业务归档用 archive（lite 暂未暴露业务删除路由）。
- 主机转移(transfer) 在上游是专用动作（edit_biz_host / host_transfer_across_business 等），
  lite 用独立的 TRANSFER 动作区分于主机本身的 update（避免「可改主机」与「可转移主机」混为一谈）。
"""


class Action:
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    FIND = "find"
    TRANSFER = "transfer"   # 主机转移（对应上游 edit_biz_host / host_transfer_* 专用动作）
    # 以下两个：上游 meta.Action 有定义，但模型实例不支持（parser 已逐实例展开）。
    # 保留仅用于兼容 cc_AuthPolicy 中的历史策略行。
    UPDATE_MANY = "updateMany"
    DELETE_MANY = "deleteMany"


class ResourceType:
    MODEL_INSTANCE = "modelInstance"
    HOST_INSTANCE = "hostInstance"
    BUSINESS = "business"
    BIZ_TOPOLOGY = "biz_topology"   # 集群/模块/主线实例（上游 IAM 侧统一为 biz_topology）
    MODEL = "model"


class ResourceAttribute:
    """一次鉴权请求的资源描述（对齐上游 ac/meta.ResourceAttribute）

    - type:        ResourceType
    - action:      Action
    - obj_id:      模型 ID（如 bk_slb）或拓扑固定值（'biz_topology'），模型级作用域，与实例 ID 正交
    - instance_id: 实例 ID（可选，单实例维度）
    - supplier:    供应商账户（多租户隔离，默认 id0；对应上游 SupplierAccount）
    - business_id: 业务 ID（拓扑权限的 biz 作用域，对应上游 ResourceAttribute.BusinessID；
                   None=全部业务。上游拓扑资源以 business 为父级作用域，lite 用独立列表达同一语义）
    """

    def __init__(self, type, action, obj_id=None, instance_id=None, supplier=None, business_id=None):
        self.type = type
        self.action = action
        self.obj_id = obj_id
        self.instance_id = instance_id
        self.supplier = supplier
        self.business_id = business_id

    def is_read(self):
        return self.action == Action.FIND
