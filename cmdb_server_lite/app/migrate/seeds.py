"""
初始化种子数据（single source of truth）

本模块只声明"初始化要写入什么数据"，不含任何数据库访问逻辑 —— 执行由
app/migrate/migrate.py 负责，SQL 由 app/sql/migrate/*.sql 提供。
这样拆分的目的：

1. **数据与执行解耦**：种子数据是可审阅的事实清单（对齐上游 bk-cmdb 的预置
   分类/模型/属性/分组/关联类型），改数据不必读 3000 行迁移流程；
2. **单一来源**：CLI（app/cli/cmdb.py）、种子脚本（scripts/seed_hosts.py）与
   迁移工具共用同一份定义，避免各处复制出现漂移；
3. **值域常量集中**：枚举/方向等取值一律引用 app/definitions.py，本模块不再
   出现字面量魔法值。

命名约定：
- ``*_SEEDS`` / ``*_SPEC``  = 待写入的数据清单
- ``*_MAP`` / ``*_DEFS``    = 迁移期用于判定或补全的映射表
- ``DEFAULT_*``             = 缺省值
"""

import json

from app.definitions import ASST_DIRECTION_SRC_TO_DEST

# 种子主机-模块挂载关系（语义化表达）
# 以 (业务, 集群名, 模块名) 表达挂载目标，运行时解析实际 bk_module_id/bk_set_id，
# 不再硬编码 ID —— 避免模块被 generate_id 重新生成后 ID 漂移导致悬空绑定。
# 目标模块/集群缺失时 seed_host_bindings() 会自动补全创建，保证挂载总能落库。
HOST_BINDING_SPEC = [
    # 主机1-2 -> 蓝鲸平台(biz2) 广州一区/web
    {"bk_host_id": 1, "bk_biz_id": 2, "bk_set_name": "广州一区", "bk_module_name": "web"},
    {"bk_host_id": 2, "bk_biz_id": 2, "bk_set_name": "广州一区", "bk_module_name": "web"},
    # 主机3 -> 广州一区/api
    {"bk_host_id": 3, "bk_biz_id": 2, "bk_set_name": "广州一区", "bk_module_name": "api"},
    # 主机4 -> 广州二区/db
    {"bk_host_id": 4, "bk_biz_id": 2, "bk_set_name": "广州二区", "bk_module_name": "db"},
    # 主机5-6 -> 正式环境(biz3) 生产集群/app
    {"bk_host_id": 5, "bk_biz_id": 3, "bk_set_name": "生产集群", "bk_module_name": "app"},
    {"bk_host_id": 6, "bk_biz_id": 3, "bk_set_name": "生产集群", "bk_module_name": "app"},
    # 主机7 -> 测试环境(biz4) 测试集群/test
    {"bk_host_id": 7, "bk_biz_id": 4, "bk_set_name": "测试集群", "bk_module_name": "test"},
    # 主机8 -> 资源池(biz1) 空闲机池/空闲机
    {"bk_host_id": 8, "bk_biz_id": 1, "bk_set_name": "空闲机池", "bk_module_name": "空闲机"},
    # 主机9-10 -> 广州一区/web
    {"bk_host_id": 9, "bk_biz_id": 2, "bk_set_name": "广州一区", "bk_module_name": "web"},
    {"bk_host_id": 10, "bk_biz_id": 2, "bk_set_name": "广州一区", "bk_module_name": "web"},
    # 主机11-12 -> 广州一区/api
    {"bk_host_id": 11, "bk_biz_id": 2, "bk_set_name": "广州一区", "bk_module_name": "api"},
    {"bk_host_id": 12, "bk_biz_id": 2, "bk_set_name": "广州一区", "bk_module_name": "api"},
    # 主机13-14 -> 广州二区/db
    {"bk_host_id": 13, "bk_biz_id": 2, "bk_set_name": "广州二区", "bk_module_name": "db"},
    {"bk_host_id": 14, "bk_biz_id": 2, "bk_set_name": "广州二区", "bk_module_name": "db"},
    # 主机15-18 -> 生产集群/app
    {"bk_host_id": 15, "bk_biz_id": 3, "bk_set_name": "生产集群", "bk_module_name": "app"},
    {"bk_host_id": 16, "bk_biz_id": 3, "bk_set_name": "生产集群", "bk_module_name": "app"},
    {"bk_host_id": 17, "bk_biz_id": 3, "bk_set_name": "生产集群", "bk_module_name": "app"},
    {"bk_host_id": 18, "bk_biz_id": 3, "bk_set_name": "生产集群", "bk_module_name": "app"},
    # 主机19-20 -> 测试集群/test
    {"bk_host_id": 19, "bk_biz_id": 4, "bk_set_name": "测试集群", "bk_module_name": "test"},
    {"bk_host_id": 20, "bk_biz_id": 4, "bk_set_name": "测试集群", "bk_module_name": "test"},
    # 主机21 -> 蓝鲸平台(biz2) 空闲机池/空闲机
    {"bk_host_id": 21, "bk_biz_id": 2, "bk_set_name": "空闲机池", "bk_module_name": "空闲机"},
]


def convert_enum_option(option_list, default_index=None):
    """
    将简单的字符串数组格式转换为原项目标准的枚举选项格式
    
    Args:
        option_list: 简单字符串数组，如 ["选项1", "选项2", "选项3"]
        default_index: 默认选中的索引（可选），从0开始
    
    Returns:
        JSON字符串，符合原项目EnumVal格式
    """
    if not option_list:
        return None
    
    enum_options = []
    for idx, option_text in enumerate(option_list):
        # 使用字符串本身作为ID（URL安全）
        option_id = str(option_text).strip()
        enum_options.append({
            "id": option_id,
            "name": str(option_text).strip(),
            "type": "text",
            "is_default": True if default_index is not None and idx == default_index else False
        })
    
    return json.dumps(enum_options, ensure_ascii=False)


def parse_enum_option(json_string):
    """
    解析JSON字符串为枚举选项列表
    
    Args:
        json_string: JSON格式的枚举选项字符串
    
    Returns:
        枚举选项列表
    """
    if not json_string:
        return []
    
    if isinstance(json_string, list):
        return json_string
    
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return []

# 系统字段列表
SYSTEM_FIELDS = {
    '_id', 
    'id', 
    'bk_inst_id', 
    'bk_inst_name', 
    'bk_obj_id', 
    'bk_supplier_account', 
    'create_time', 
    'last_time', 
    'bk_operate_time',
    'bk_created_by',
    'bk_created_at',
    'bk_updated_by',
    'bk_updated_at',
    'modifier'
}

DEFAULT_OBJ_ICON = 'icon-cc-default'
DEFAULT_CLASSIFICATION_ICON = 'icon-cc-default'
DEFAULT_ASST_ICON = 'icon-cc-default'

# 系统属性定义
# 与原项目规则保持一致，参考:
# - /workspace/bk-cmdb/src/scene_server/admin_server/upgrader/y3.10.202302062350/add_project.go (bk_project 的 id 字段)
# - /workspace/bk-cmdb/src/scene_server/admin_server/upgrader/history/v3.0.8/objAttDescData.go (bk_inst_name 字段)
# - /workspace/bk-cmdb/src/source_controller/coreservice/core/instances/instance_validate.go (bk_obj_id 跳过验证)
#
# 原项目规则:
# - bk_isapi=true: API 字段，对页面不可见（前端过滤）
# - bk_issystem=true: 系统内部字段，不返回前端
# - id 字段: 原项目仅在 bk_project 模型显式创建，只设 bk_isapi=true，不设 bk_issystem
# - bk_inst_id 字段: 原项目不在 cc_ObjAttDes 中维护，简化版保留时参考 id 规则
# - bk_inst_name 字段: 原项目配置 ispre=true, isrequired=true, isonly=true, editable=true，bk_issystem=false（用户可见可编辑）
# - bk_obj_id 字段: 原项目不在 cc_ObjAttDes 中维护，由系统自动注入；简化版保留时设 bk_issystem=true（系统内部字段）
SYSTEM_PROPERTIES = [
    {
        "bk_property_id": "id",
        "bk_property_name": "数据ID",
        "bk_property_type": "int",
        "isrequired": False,
        "isreadonly": True,
        "isonly": False,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": False,
        "bk_isapi": True,   # API 字段，前端隐藏（原项目 bk_project 规则）
        "bk_issystem": False,  # 修复：原项目 id 字段只设 bk_isapi=true，不设 bk_issystem
        "ispre": True,
        "bk_property_index": -1,
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    },
    {
        "bk_property_id": "bk_inst_id",
        "bk_property_name": "实例ID",
        "bk_property_type": "int",
        "isrequired": False,
        "isreadonly": True,
        "isonly": False,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": False,
        "bk_isapi": True,  # API 字段，前端隐藏（参考 id 字段规则）
        "bk_issystem": False,  # 修复：参考 id 字段规则，API 字段非系统字段
        "ispre": True,
        "bk_property_index": 0,
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    },
    {
        "bk_property_id": "bk_inst_name",
        "bk_property_name": "实例名称",
        "bk_property_type": "singlechar",
        "isrequired": True,
        "isreadonly": False,
        "isonly": True,
        "editable": True,
        "bk_ispassword": False,
        "bk_ishidden": False,
        "bk_isapi": False,
        "bk_issystem": False,  # 修复：原项目 bk_inst_name 不是系统字段，用户可见可编辑
        "ispre": True,
        "bk_property_index": 1,
        "bk_property_group": "default",
        "placeholder": "请输入实例名称，用于标识该实例",
        "unit": "",
        "option": None
    },
    {
        "bk_property_id": "bk_obj_id",
        "bk_property_name": "模型ID",
        "bk_property_type": "singlechar",
        "isrequired": True,
        "isreadonly": True,
        "isonly": False,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": True,
        "bk_isapi": True,
        "bk_issystem": True,  # 保持：系统内部字段，由后端自动注入，不返回前端
        "ispre": True,
        "bk_property_index": 2,
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    }
]

# 内置时间属性（创建时间 / 最后修改时间）
# 规则与 biz/set/module（见 BUILTIN_MODEL_ATTRIBUTES）保持一致：
# - bk_property_type=time，ispre=true（内置，不可删）
# - isreadonly=true / editable=false：值由系统写入，用户不可改
# - bk_isapi=false / bk_issystem=false：对页面可见（详情页、列表字段可选）
# - bk_property_group=default：与 biz 一样落在「基础信息」分组
# 索引取极大值，保证 UI 属性排序（组内按 bk_property_index 升序）时永远排在最后，
# 且不与业务属性（现有模型最大 index 为 34）或后续 CLI 新增属性冲突。
BUILTIN_TIME_PROPERTY_INDEX = {
    "create_time": 9998,
    "last_time": 9999,
}

BUILTIN_TIME_PROPERTIES = [
    {
        "bk_property_id": "create_time",
        "bk_property_name": "创建时间",
        "bk_property_type": "time",
        "isrequired": False,
        "isreadonly": True,
        "isonly": False,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": False,
        "bk_isapi": False,
        "bk_issystem": False,
        "ispre": True,
        "bk_property_index": BUILTIN_TIME_PROPERTY_INDEX["create_time"],
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    },
    {
        "bk_property_id": "last_time",
        "bk_property_name": "最后修改时间",
        "bk_property_type": "time",
        "isrequired": False,
        "isreadonly": True,
        "isonly": False,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": False,
        "bk_isapi": False,
        "bk_issystem": False,
        "ispre": True,
        "bk_property_index": BUILTIN_TIME_PROPERTY_INDEX["last_time"],
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    }
]

# 系统属性 = 4 个标识属性（id / bk_inst_id / bk_inst_name / bk_obj_id）
#          + 2 个内置时间属性（create_time / last_time）
# 该列表同时被 migrate_attributes（存量模型）与 CLI create_model_core（新建模型）消费，
# 保证「通用普通模型 + host」与 biz/set/module 一样自带创建时间 / 最后修改时间。
SYSTEM_PROPERTIES = SYSTEM_PROPERTIES + BUILTIN_TIME_PROPERTIES

# 内置模型定义（biz/set/module）
# 这些模型有独立的表（cc_ApplicationBase/cc_SetBase/cc_ModuleBase）
# 需要在 cc_ObjDes 和 cc_ObjAttDes 中注册，以便前端正常显示属性
BUILTIN_MODELS = [
    {
        "bk_obj_id": "biz",
        "bk_obj_name": "业务",
        "bk_obj_icon": "icon-cc-business",
        "bk_classification_id": "bk_biz_topo",
        "ispre": True,
        "obj_sort_number": -3,
        # 业务也纳入资源目录（与 set/module 一致），默认初始化即可看到业务模型实例列表
        "bk_isresourcedir": 1
    },
    {
        "bk_obj_id": "set",
        "bk_obj_name": "集群",
        "bk_obj_icon": "icon-cc-set",
        "bk_classification_id": "bk_biz_topo",
        "ispre": True,
        "obj_sort_number": -2,
        # 集群/模块需在资源目录展示其模型实例列表（见资源实例页 filteredClassifications）
        "bk_isresourcedir": 1
    },
    {
        "bk_obj_id": "module",
        "bk_obj_name": "模块",
        "bk_obj_icon": "icon-cc-module",
        "bk_classification_id": "bk_biz_topo",
        "ispre": True,
        "obj_sort_number": -1,
        "bk_isresourcedir": 1
    }
]

# 内置模型属性定义
BUILTIN_MODEL_ATTRIBUTES = {
    "biz": [
        {"bk_property_id": "bk_biz_id", "bk_property_name": "业务ID", "bk_property_type": "int",
         "isrequired": True, "isreadonly": True, "isonly": True, "editable": False,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": True, "bk_issystem": False,
         "ispre": True, "bk_property_index": 0, "bk_property_group": "default"},
        {"bk_property_id": "bk_biz_name", "bk_property_name": "业务名称", "bk_property_type": "singlechar",
         "isrequired": True, "isreadonly": False, "isonly": True, "editable": True,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 1, "bk_property_group": "default"},
        {"bk_property_id": "default", "bk_property_name": "默认", "bk_property_type": "int",
         "isrequired": False, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": True, "bk_isapi": False, "bk_issystem": True,
         "ispre": True, "bk_property_index": 10, "bk_property_group": "default"},
        {"bk_property_id": "creator", "bk_property_name": "创建人", "bk_property_type": "singlechar",
         "isrequired": False, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 20, "bk_property_group": "default"},
        {"bk_property_id": "modifier", "bk_property_name": "修改人", "bk_property_type": "singlechar",
         "isrequired": False, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 21, "bk_property_group": "default"},
        {"bk_property_id": "create_time", "bk_property_name": "创建时间", "bk_property_type": "time",
         "isrequired": False, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 22, "bk_property_group": "default"},
        {"bk_property_id": "last_time", "bk_property_name": "最后修改时间", "bk_property_type": "time",
         "isrequired": False, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 23, "bk_property_group": "default"},
    ],
    "set": [
        {"bk_property_id": "bk_set_id", "bk_property_name": "集群ID", "bk_property_type": "int",
         "isrequired": True, "isreadonly": True, "isonly": True, "editable": False,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": True, "bk_issystem": False,
         "ispre": True, "bk_property_index": 0, "bk_property_group": "default"},
        {"bk_property_id": "bk_set_name", "bk_property_name": "集群名称", "bk_property_type": "singlechar",
         "isrequired": True, "isreadonly": False, "isonly": False, "editable": True,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 1, "bk_property_group": "default"},
        {"bk_property_id": "bk_biz_id", "bk_property_name": "业务ID", "bk_property_type": "int",
         "isrequired": True, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": True, "bk_isapi": False, "bk_issystem": True,
         "ispre": True, "bk_property_index": 2, "bk_property_group": "default"},
        {"bk_property_id": "bk_parent_id", "bk_property_name": "父节点ID", "bk_property_type": "int",
         "isrequired": True, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": True, "bk_isapi": False, "bk_issystem": True,
         "ispre": True, "bk_property_index": 3, "bk_property_group": "default"},
        {"bk_property_id": "bk_set_desc", "bk_property_name": "集群描述", "bk_property_type": "longchar",
         "isrequired": False, "isreadonly": False, "isonly": False, "editable": True,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 5, "bk_property_group": "default"},
        {"bk_property_id": "bk_set_env", "bk_property_name": "环境类型", "bk_property_type": "enum",
         "isrequired": False, "isreadonly": False, "isonly": False, "editable": True,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 6, "bk_property_group": "default",
         "option": [
             {"id": "1", "name": "测试环境", "type": "text", "is_default": False},
             {"id": "2", "name": "体验环境", "type": "text", "is_default": False},
             {"id": "3", "name": "正式环境", "type": "text", "is_default": True}
         ]},
        {"bk_property_id": "bk_service_status", "bk_property_name": "服务状态", "bk_property_type": "enum",
         "isrequired": False, "isreadonly": False, "isonly": False, "editable": True,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 7, "bk_property_group": "default",
         "option": [
             {"id": "1", "name": "开放", "type": "text", "is_default": True},
             {"id": "2", "name": "关闭", "type": "text", "is_default": False}
         ]},
        {"bk_property_id": "default", "bk_property_name": "默认", "bk_property_type": "int",
         "isrequired": False, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": True, "bk_isapi": False, "bk_issystem": True,
         "ispre": True, "bk_property_index": 10, "bk_property_group": "default"},
        {"bk_property_id": "creator", "bk_property_name": "创建人", "bk_property_type": "singlechar",
         "isrequired": False, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 20, "bk_property_group": "default"},
        {"bk_property_id": "modifier", "bk_property_name": "修改人", "bk_property_type": "singlechar",
         "isrequired": False, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 21, "bk_property_group": "default"},
        {"bk_property_id": "create_time", "bk_property_name": "创建时间", "bk_property_type": "time",
         "isrequired": False, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 22, "bk_property_group": "default"},
        {"bk_property_id": "last_time", "bk_property_name": "最后修改时间", "bk_property_type": "time",
         "isrequired": False, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 23, "bk_property_group": "default"},
    ],
    "module": [
        {"bk_property_id": "bk_module_id", "bk_property_name": "模块ID", "bk_property_type": "int",
         "isrequired": True, "isreadonly": True, "isonly": True, "editable": False,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": True, "bk_issystem": False,
         "ispre": True, "bk_property_index": 0, "bk_property_group": "default"},
        {"bk_property_id": "bk_module_name", "bk_property_name": "模块名称", "bk_property_type": "singlechar",
         "isrequired": True, "isreadonly": False, "isonly": False, "editable": True,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 1, "bk_property_group": "default"},
        {"bk_property_id": "service_category_id", "bk_property_name": "服务分类", "bk_property_type": "int",
         "isrequired": False, "isreadonly": False, "isonly": False, "editable": True,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": True, "bk_issystem": False,
         "ispre": True, "bk_property_index": 5, "bk_property_group": "default"},
        {"bk_property_id": "bk_module_type", "bk_property_name": "模块类型", "bk_property_type": "enum",
         "isrequired": False, "isreadonly": False, "isonly": False, "editable": True,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 6, "bk_property_group": "default",
         "option": [
             {"id": "1", "name": "普通", "type": "text", "is_default": True},
             {"id": "2", "name": "数据库", "type": "text", "is_default": False}
         ]},
        {"bk_property_id": "bk_biz_id", "bk_property_name": "业务ID", "bk_property_type": "int",
         "isrequired": True, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": True, "bk_isapi": False, "bk_issystem": True,
         "ispre": True, "bk_property_index": 2, "bk_property_group": "default"},
        {"bk_property_id": "bk_set_id", "bk_property_name": "集群ID", "bk_property_type": "int",
         "isrequired": True, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": True, "bk_isapi": False, "bk_issystem": True,
         "ispre": True, "bk_property_index": 3, "bk_property_group": "default"},
        {"bk_property_id": "bk_parent_id", "bk_property_name": "父节点ID", "bk_property_type": "int",
         "isrequired": True, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": True, "bk_isapi": False, "bk_issystem": True,
         "ispre": True, "bk_property_index": 4, "bk_property_group": "default"},
        {"bk_property_id": "default", "bk_property_name": "默认", "bk_property_type": "int",
         "isrequired": False, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": True, "bk_isapi": False, "bk_issystem": True,
         "ispre": True, "bk_property_index": 10, "bk_property_group": "default"},
        {"bk_property_id": "creator", "bk_property_name": "创建人", "bk_property_type": "singlechar",
         "isrequired": False, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 20, "bk_property_group": "default"},
        {"bk_property_id": "modifier", "bk_property_name": "修改人", "bk_property_type": "singlechar",
         "isrequired": False, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 21, "bk_property_group": "default"},
        {"bk_property_id": "create_time", "bk_property_name": "创建时间", "bk_property_type": "time",
         "isrequired": False, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 22, "bk_property_group": "default"},
        {"bk_property_id": "last_time", "bk_property_name": "最后修改时间", "bk_property_type": "time",
         "isrequired": False, "isreadonly": True, "isonly": False, "editable": False,
         "bk_ispassword": False, "bk_ishidden": False, "bk_isapi": False, "bk_issystem": False,
         "ispre": True, "bk_property_index": 23, "bk_property_group": "default"},
    ]
}

# 模型分类映射
MODEL_CLASSIFICATION_MAP = {
    "bk_switch": "bk_network",
    "host": "bk_host_manage",
    "bk_slb": "bk_loadbalance",
    "bk_slb_server": "bk_loadbalance",
    "bk_slb_listener": "bk_loadbalance",
}

# 分类定义
CLASSIFICATIONS = [
    {"id": 1, "bk_classification_id": "bk_network", "bk_classification_name": "网络", "bk_classification_icon": "icon-cc-network-segment", "ispre": True, "classification_index": 1},
    {"id": 2, "bk_classification_id": "bk_host_manage", "bk_classification_name": "主机管理", "bk_classification_icon": "icon-cc-host", "ispre": True, "classification_index": 2},
    {"id": 3, "bk_classification_id": "bk_loadbalance", "bk_classification_name": "负载均衡", "bk_classification_icon": "icon-cc-balance", "ispre": True, "classification_index": 3},
    {"id": 4, "bk_classification_id": "bk_biz_topo", "bk_classification_name": "业务拓扑", "bk_classification_icon": "icon-cc-business", "ispre": True, "classification_index": 4},
]

# 属性分组定义（对齐上游 bk-cmdb）
#
# 术语澄清（易错点）：
#   bk_group_id / bk_property_group  = 分组【ID】，上游 NewGroupID(true) 固定返回小写 "default"
#                                      （src/scene_server/topo_server/logics/model/group.go:335-341）
#   bk_group_name                    = 分组【显示名】，按模型类型区分：
#                                      - 内置模型(biz/set/module/host)：「基础信息」(BaseInfoName)
#                                        （admin_server/common/definitions.go:22）
#                                      - 通用/普通模型：首字母大写的 "Default"
#                                        （logics/model/object.go:150 硬编码），属 bk_group_name 而非 ID
#   切勿把 "Default" 写进 bk_property_group（那是分组 ID，固定小写 "default"）。
#
# 上游内置模型只有 default 一个通用分组（addPresetObjects.go:242-268），
# 不存在 base 分组；host 的自动发现分组 ID 是 auto 而非 agent。
# 默认分组显示名：内置模型 =「基础信息」，通用/普通模型 =「Default」（见 DEFAULT_GROUP_BUILTIN_MODELS）。
PROPERTY_GROUPS = [
    {"id": 1, "bk_group_id": "default", "bk_group_name": "基础信息", "bk_isdefault": True,
     "is_collapse": False, "ispre": True, "bk_group_index": -1},
]

# 默认分组显示名：区分内置模型与通用/普通模型（对齐上游）。
BUILTIN_DEFAULT_GROUP_NAME = "基础信息"   # 内置模型(biz/set/module/host) 默认分组显示名
GENERIC_DEFAULT_GROUP_NAME = "Default"    # 通用/普通模型 默认分组显示名（上游硬编码）
# 上游内置模型集合：其默认分组显示名用「基础信息」；其余模型（bk_switch/bk_slb/bk_deployment 等）
# 均为通用/普通模型，默认分组显示名用「Default」。
# 注意：区别于上方 BUILTIN_MODELS（内置模型定义列表），本集合仅用于默认分组显示名判定。
DEFAULT_GROUP_BUILTIN_MODELS = {"biz", "set", "module", "host"}

# 非通用分组定义：仅在特定模型上出现，由属性实际引用反推补全时取此处的名称与序号。
# 对齐 admin_server/common/definitions.go 与 addPresetObjects.go 的 GroupIndex。
# 显示名与 app/definitions.py 的 KNOWN_GROUP_NAMES（CLI 共用单一来源）保持一致，
# migrate_property_groups 补全分组时已优先用 KNOWN_GROUP_NAMES 反查，避免漂移。
EXTRA_GROUP_DEFS = {
    "auto": {"bk_group_name": "自动发现信息（需要安装agent）", "bk_group_index": 3},
    "role": {"bk_group_name": "角色", "bk_group_index": 2},
    "proc_port": {"bk_group_name": "监听信息", "bk_group_index": 2},
}

# 历史分组 ID 归并规则：旧值 -> 上游标准值。
# base 是 lite 早期自造的分组，上游内置模型的「基础信息」分组 ID 就是 default，故并回 default；
# agent 是 lite 对上游 auto（HostAutoFields）的误写，直接改名。
GROUP_ID_MIGRATION = {
    "base": "default",
    "agent": "auto",
}

# 需要更新分组的属性映射（属性ID -> 分组ID）
# 全部归入 default：对齐上游各 *Row() 中标注为 groupBaseInfo（= mCommon.BaseInfo = "default"）的属性，
# 见 objAttDescData.go:29 `groupBaseInfo = mCommon.BaseInfo` 及 HostRow() 的「基本信息分组」注释。
PROPERTY_GROUP_UPDATE_MAP = {
    "name": "default",
    "bk_inst_name": "default",
    "bk_host_innerip": "default",
    "bk_host_outerip": "default",
    "bk_cloud_id": "default",
    "bk_switch_name": "default",
    "bk_switch_ip": "default",
    "bk_lb_name": "default",
    "bk_server_name": "default",
    "bk_listener_name": "default",
    "description": "default",
    "operator": "default",
    "bk_bak_operator": "default",
    "bk_asset_id": "default",
    "bk_sn": "default",
    "bk_comment": "default",
    "bk_service_term": "default",
    "bk_sla": "default",
    "bk_state_name": "default",
    "bk_province_name": "default",
    "bk_isp_name": "default",
}


# ---------------------------------------------------------------------------
# 关联类型（cc_AsstDes）预置种子
# ---------------------------------------------------------------------------
# 对齐上游 addPresetAssociationType
# （src/scene_server/admin_server/upgrader/history/x18.10.30.01/association.go:88-155）。
#
# bk_asst_id 标准值（来自上游 common/definitions.go）：
#   bk_mainline 主线 / belong 属于 / group 分组 / run 运行 / connect 连接 / default 默认
#
# direction：上游 6 个预置类型全部使用 metadata.DestinationToSource，其取值为
# 字符串 "src_to_dest"（上游常量名与取值错位，详见 app/definitions.py 说明）。
# 早期 lite 曾写入 'forward' —— 不属上游值域，方向语义实际不可用；现统一引用
# ASST_DIRECTION_SRC_TO_DEST 常量，存量库由 migrate 步骤 9.1
# normalize_association_directions() 归一。
#
# 显示文案（src_des / dest_des）保留 lite 既有措辞，不强行改为上游文案，避免
# 既有 UI 展示与用户认知发生变化（上游为 default=关联/被关联、group=组成/组成于、
# connect=上联/下联）。
#
# ispre=True 表示预置类型：接口层禁止修改 bk_asst_id、禁止删除
# （见 app/service/association_type_service.py 的删除双重保护）。
ASSOCIATION_KIND_SEEDS = [
    {
        "bk_asst_id": "default",
        "bk_asst_name": "默认",
        "src_des": "指向",
        "dest_des": "被指向",
        "direction": ASST_DIRECTION_SRC_TO_DEST,
        "bk_supplier_account": "0",
        "ispre": True,
    },
    {
        "bk_asst_id": "belong",
        "bk_asst_name": "属于",
        "src_des": "属于",
        "dest_des": "包含",
        "direction": ASST_DIRECTION_SRC_TO_DEST,
        "bk_supplier_account": "0",
        "ispre": True,
    },
    {
        "bk_asst_id": "connect",
        "bk_asst_name": "连接",
        "src_des": "连接",
        "dest_des": "被连接",
        "direction": ASST_DIRECTION_SRC_TO_DEST,
        "bk_supplier_account": "0",
        "ispre": True,
    },
    {
        "bk_asst_id": "group",
        "bk_asst_name": "分组",
        "src_des": "分组",
        "dest_des": "被分组",
        "direction": ASST_DIRECTION_SRC_TO_DEST,
        "bk_supplier_account": "0",
        "ispre": True,
    },
    {
        "bk_asst_id": "run",
        "bk_asst_name": "运行",
        "src_des": "运行于",
        "dest_des": "运行",
        "direction": ASST_DIRECTION_SRC_TO_DEST,
        "bk_supplier_account": "0",
        "ispre": True,
    },
    {
        "bk_asst_id": "install",
        "bk_asst_name": "安装",
        "src_des": "安装",
        "dest_des": "运行于",
        "direction": ASST_DIRECTION_SRC_TO_DEST,
        "bk_supplier_account": "0",
        "ispre": True,
    },
    # bk_mainline：主线关联类型。上游 addPresetAssociationType 预置了它
    # （src_des=组成 / dest_des=组成于 / direction=src_to_dest / ispre=true），
    # 而 lite 此前只在 cc_ObjAsst 写入 bk_asst_id='bk_mainline' 的模型关联，
    # 却没在 cc_AsstDes 注册对应类型 —— 形成悬空引用（关联类型列表查不到，
    # 主线关联的 src_des/dest_des 无从取得）。此处补齐，与上游对齐。
    # 注：上游 bk_asst_name 为空串，lite 该列 NOT NULL，故取显示名"主线"。
    {
        "bk_asst_id": "bk_mainline",
        "bk_asst_name": "主线",
        "src_des": "组成",
        "dest_des": "组成于",
        "direction": ASST_DIRECTION_SRC_TO_DEST,
        "bk_supplier_account": "0",
        "ispre": True,
    },
]


# ---------------------------------------------------------------------------
# 模型关联（cc_ObjAsst）预置种子
# ---------------------------------------------------------------------------
# bk_obj_asst_id 格式：{源模型ID}_{关联类型ID}_{目标模型ID}
#   例：bk_slb_default_bk_slb_server = bk_slb + default + bk_slb_server
# mapping 取值：1:1 / 1:n / n:n（对齐上游 metadata.MappingType）
# on_delete 取值：none / delete_src / delete_dest（对齐上游 metadata.DeleteAction）
OBJECT_ASSOCIATION_SEEDS = [
    {
        "bk_obj_id": "bk_slb",
        "target_obj_id": "bk_slb_server",
        "target_obj_name": "后端服务器",
        "bk_asst_id": "default",
        "bk_obj_asst_id": "bk_slb_default_bk_slb_server",
        "bk_obj_asst_name": "指向后端服务器",
        "bk_supplier_account": "0",
        "mapping": "n:n",
        "on_delete": "none",
    },
    {
        "bk_obj_id": "bk_slb",
        "target_obj_id": "bk_slb_listener",
        "target_obj_name": "监听器",
        "bk_asst_id": "default",
        "bk_obj_asst_id": "bk_slb_default_bk_slb_listener",
        "bk_obj_asst_name": "指向监听器",
        "bk_supplier_account": "0",
        "mapping": "1:n",
        "on_delete": "none",
    },
    {
        "bk_obj_id": "host",
        "target_obj_id": "bk_slb",
        "target_obj_name": "负载均衡",
        "bk_asst_id": "install",
        "bk_obj_asst_id": "host_install_slb",
        "bk_obj_asst_name": "主机安装SLB",
        "bk_supplier_account": "0",
        "mapping": "1:1",
        "on_delete": "none",
    },
]
