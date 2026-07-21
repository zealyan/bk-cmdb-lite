"""
业务拓扑树服务

基于原项目蓝鲸 CMDB 的主线拓扑（Mainline Topo）实现：
- TopoModelMainline: 模型拓扑树（biz -> set -> module）
- TopoInstance: 实例拓扑树（业务 -> 集群 -> 模块），支持 with_statistics

参考原项目：
- src/source_controller/coreservice/core/mainline/model.go
- src/source_controller/coreservice/core/mainline/instance.go
- src/common/metadata/core_service.go
"""
import json
from typing import Dict, List, Optional, Any
from app.db.executor import query_all, query_one

# 主线拓扑内置模型ID
MAINLINE_MODEL_BIZ = 'biz'
MAINLINE_MODEL_SET = 'set'
MAINLINE_MODEL_MODULE = 'module'

# 主线拓扑模型层级（从根到叶）
MAINLINE_MODEL_LEVELS = [MAINLINE_MODEL_BIZ, MAINLINE_MODEL_SET, MAINLINE_MODEL_MODULE]

# 模型对应实例表名
MODEL_INSTANCE_TABLE = {
    MAINLINE_MODEL_BIZ: 'cc_ApplicationBase',
    MAINLINE_MODEL_SET: 'cc_SetBase',
    MAINLINE_MODEL_MODULE: 'cc_ModuleBase',
}

# 模型对应主键字段名
MODEL_ID_FIELD = {
    MAINLINE_MODEL_BIZ: 'bk_biz_id',
    MAINLINE_MODEL_SET: 'bk_set_id',
    MAINLINE_MODEL_MODULE: 'bk_module_id',
}

# 模型对应名称字段名
MODEL_NAME_FIELD = {
    MAINLINE_MODEL_BIZ: 'bk_biz_name',
    MAINLINE_MODEL_SET: 'bk_set_name',
    MAINLINE_MODEL_MODULE: 'bk_module_name',
}

# 模型对应父实例ID字段名
MODEL_PARENT_FIELD = {
    MAINLINE_MODEL_SET: 'bk_parent_id',
    MAINLINE_MODEL_MODULE: 'bk_parent_id',
}

DEFAULT_SUPPLIER = '0'


class TopoModelNode:
    """
    模型拓扑节点
    对应原项目 metadata.TopoModelNode
    """
    def __init__(self, object_id: str):
        self.object_id = object_id
        self.children: List['TopoModelNode'] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'bk_obj_id': self.object_id,
            'children': [child.to_dict() for child in self.children],
        }

    def leftest_object_id_list(self) -> List[str]:
        """
        提取最左路径的object id列表
        对应原项目 TopoModelNode.LeftestObjectIDList()
        """
        ids = []
        node = self
        while True:
            ids.append(node.object_id)
            if not node.children:
                break
            node = node.children[0]
        return ids


class TopoInstanceNode:
    """
    实例拓扑节点
    对应原项目 metadata.TopoInstanceNode
    """
    def __init__(self, object_id: str, instance_id: int, instance_name: str,
                 detail: Dict[str, Any] = None, default: int = 0):
        self.object_id = object_id
        self.instance_id = instance_id
        self.instance_name = instance_name
        self.detail = detail or {}
        self.default = default  # default 字段：0=普通, 1=空闲机, 2=故障机, 3=待回收
        self.children: List['TopoInstanceNode'] = []
        self.count = 0  # 子节点数量统计（with_statistics时使用）

    def to_dict(self, with_statistics: bool = False) -> Dict[str, Any]:
        result = {
            'bk_obj_id': self.object_id,
            'bk_inst_id': self.instance_id,
            'bk_inst_name': self.instance_name,
            'default': self.default,  # 返回 default 字段
        }
        if with_statistics:
            result['count'] = self.count
        if self.children:
            result['child'] = [child.to_dict(with_statistics) for child in self.children]
        else:
            result['child'] = []
        return result

    def to_simplify(self) -> Dict[str, Any]:
        return {
            'bk_obj_id': self.object_id,
            'bk_inst_id': self.instance_id,
            'bk_inst_name': self.instance_name,
        }


def get_mainline_model_top(supplier_account: str = DEFAULT_SUPPLIER) -> TopoModelNode:
    """
    获取主线模型拓扑树（TopoModelMainline）

    从 cc_ObjAsst 表查询 bk_mainline 关联关系，构建模型拓扑树。
    对应原项目 mainline.ModelMainline.GetRoot()

    Args:
        supplier_account: 供应商账号，默认 '0'

    Returns:
        TopoModelNode 根节点（biz）
    """
    sql = """
        SELECT bk_obj_id, target_obj_id, bk_obj_asst_id
        FROM cc_ObjAsst
        WHERE bk_asst_id = 'bk_mainline'
          AND bk_supplier_account = :supplier
        ORDER BY bk_obj_asst_id
    """
    associations = query_all(sql, {'supplier': supplier_account})

    if not associations:
        root = TopoModelNode(MAINLINE_MODEL_BIZ)
        set_node = TopoModelNode(MAINLINE_MODEL_SET)
        module_node = TopoModelNode(MAINLINE_MODEL_MODULE)
        set_node.children.append(module_node)
        root.children.append(set_node)
        return root

    node_map: Dict[str, TopoModelNode] = {}
    root = None

    for assoc in associations:
        parent_obj_id = assoc['target_obj_id']
        child_obj_id = assoc['bk_obj_id']

        if parent_obj_id not in node_map:
            node_map[parent_obj_id] = TopoModelNode(parent_obj_id)
        parent_node = node_map[parent_obj_id]

        if parent_obj_id == MAINLINE_MODEL_BIZ:
            root = parent_node

        if child_obj_id not in node_map:
            node_map[child_obj_id] = TopoModelNode(child_obj_id)
        child_node = node_map[child_obj_id]

        parent_node.children.append(child_node)

    if root is None:
        root = TopoModelNode(MAINLINE_MODEL_BIZ)
        if MAINLINE_MODEL_SET in node_map:
            root.children.append(node_map[MAINLINE_MODEL_SET])

    return root


def _load_instances(model_id: str, bk_biz_id: int,
                    supplier_account: str = DEFAULT_SUPPLIER) -> List[Dict[str, Any]]:
    """
    加载指定模型的实例列表

    Args:
        model_id: 模型ID（biz/set/module）
        bk_biz_id: 业务ID
        supplier_account: 供应商账号

    Returns:
        实例列表
    """
    table = MODEL_INSTANCE_TABLE.get(model_id)
    if not table:
        return []

    id_field = MODEL_ID_FIELD[model_id]
    name_field = MODEL_NAME_FIELD[model_id]

    if model_id == MAINLINE_MODEL_BIZ:
        # 业务表：排除资源池（default=1）
        sql = f"""
            SELECT {id_field}, {name_field}, "default", *
            FROM {table}
            WHERE bk_supplier_account = :supplier
              AND "default" = 0
            ORDER BY {id_field}
        """
    elif model_id == MAINLINE_MODEL_SET:
        # 集群表：按 default 降序排序（空闲机池 default=1 排最前面）
        sql = f"""
            SELECT {id_field}, {name_field}, "default", bk_parent_id, bk_biz_id, *
            FROM {table}
            WHERE bk_supplier_account = :supplier
              AND bk_biz_id = :bk_biz_id
            ORDER BY "default" DESC, {id_field}
        """
    else:
        # 模块表：按 default 降序排序（空闲机 default=1 排最前面）
        parent_field = MODEL_PARENT_FIELD.get(model_id, 'bk_parent_id')
        sql = f"""
            SELECT {id_field}, {name_field}, "default", {parent_field}, bk_set_id, bk_biz_id, *
            FROM {table}
            WHERE bk_supplier_account = :supplier
              AND bk_biz_id = :bk_biz_id
            ORDER BY "default" DESC, {id_field}
        """

    return query_all(sql, {'supplier': supplier_account, 'bk_biz_id': bk_biz_id})


def _get_business_instance(bk_biz_id: int,
                           supplier_account: str = DEFAULT_SUPPLIER) -> Optional[Dict[str, Any]]:
    """
    获取业务实例详情

    Args:
        bk_biz_id: 业务ID
        supplier_account: 供应商账号

    Returns:
        业务实例数据或None
    """
    sql = """
        SELECT bk_biz_id, bk_biz_name, *
        FROM cc_ApplicationBase
        WHERE bk_biz_id = :bk_biz_id
          AND bk_supplier_account = :supplier
    """
    return query_one(sql, {'bk_biz_id': bk_biz_id, 'supplier': supplier_account})


def _count_hosts_by_module(bk_biz_id: int,
                           supplier_account: str = DEFAULT_SUPPLIER) -> Dict[int, int]:
    """
    统计每个模块下的主机数量

    Args:
        bk_biz_id: 业务ID
        supplier_account: 供应商账号

    Returns:
        { module_id: host_count }
    """
    sql = """
        SELECT bk_module_id, COUNT(DISTINCT bk_host_id) as host_count
        FROM cc_ModuleHostConfig
        WHERE bk_biz_id = :bk_biz_id
          AND bk_supplier_account = :supplier
        GROUP BY bk_module_id
    """
    rows = query_all(sql, {'bk_biz_id': bk_biz_id, 'supplier': supplier_account})
    return {row['bk_module_id']: row['host_count'] for row in rows}


def get_mainline_instance_topo(bk_biz_id: int, with_detail: bool = False,
                               with_statistics: bool = False,
                               supplier_account: str = DEFAULT_SUPPLIER) -> Optional[TopoInstanceNode]:
    """
    获取主线实例拓扑树（TopoInstance）

    对应原项目 mainline.InstanceMainline.SearchMainlineInstanceTopo()
    构建结构：业务 -> 集群 -> 模块

    Args:
        bk_biz_id: 业务ID
        with_detail: 是否返回完整详情
        with_statistics: 是否返回统计信息（子节点数量）
        supplier_account: 供应商账号

    Returns:
        TopoInstanceNode 根节点（业务），不存在则返回None
    """
    model_tree = get_mainline_model_top(supplier_account)
    model_levels = model_tree.leftest_object_id_list()

    biz_instance = _get_business_instance(bk_biz_id, supplier_account)
    if not biz_instance:
        return None

    biz_name = biz_instance.get(MODEL_NAME_FIELD[MAINLINE_MODEL_BIZ], f'biz_{bk_biz_id}')
    biz_default = biz_instance.get('default', 0)
    root = TopoInstanceNode(
        object_id=MAINLINE_MODEL_BIZ,
        instance_id=bk_biz_id,
        instance_name=biz_name,
        detail=biz_instance if with_detail else {},
        default=biz_default
    )

    set_instances = _load_instances(MAINLINE_MODEL_SET, bk_biz_id, supplier_account)
    module_instances = _load_instances(MAINLINE_MODEL_MODULE, bk_biz_id, supplier_account)

    module_host_count = {}
    if with_statistics:
        module_host_count = _count_hosts_by_module(bk_biz_id, supplier_account)

    set_node_map: Dict[int, TopoInstanceNode] = {}
    for inst in set_instances:
        set_id = inst[MODEL_ID_FIELD[MAINLINE_MODEL_SET]]
        set_name = inst.get(MODEL_NAME_FIELD[MAINLINE_MODEL_SET], f'set_{set_id}')
        set_default = inst.get('default', 0)
        set_node = TopoInstanceNode(
            object_id=MAINLINE_MODEL_SET,
            instance_id=set_id,
            instance_name=set_name,
            detail=inst if with_detail else {},
            default=set_default
        )
        set_node_map[set_id] = set_node
        root.children.append(set_node)

    for inst in module_instances:
        module_id = inst[MODEL_ID_FIELD[MAINLINE_MODEL_MODULE]]
        module_name = inst.get(MODEL_NAME_FIELD[MAINLINE_MODEL_MODULE], f'module_{module_id}')
        module_default = inst.get('default', 0)
        parent_id = inst.get('bk_set_id') or inst.get(MODEL_PARENT_FIELD.get(MAINLINE_MODEL_MODULE, 'bk_parent_id'))

        module_node = TopoInstanceNode(
            object_id=MAINLINE_MODEL_MODULE,
            instance_id=module_id,
            instance_name=module_name,
            detail=inst if with_detail else {},
            default=module_default
        )

        if with_statistics:
            module_node.count = module_host_count.get(module_id, 0)

        if parent_id and parent_id in set_node_map:
            set_node_map[parent_id].children.append(module_node)

    if with_statistics:
        for set_node in root.children:
            set_node.count = sum(child.count for child in set_node.children)
        root.count = sum(child.count for child in root.children)

    return root


def get_biz_list(supplier_account: str = DEFAULT_SUPPLIER) -> List[Dict[str, Any]]:
    """
    获取业务列表

    Args:
        supplier_account: 供应商账号

    Returns:
        业务列表
    """
    sql = """
        SELECT bk_biz_id, bk_biz_name, "default", bk_supplier_account
        FROM cc_ApplicationBase
        WHERE bk_supplier_account = :supplier
        ORDER BY bk_biz_id
    """
    return query_all(sql, {'supplier': supplier_account})


def get_biz_list_with_statistics(supplier_account: str = DEFAULT_SUPPLIER) -> List[Dict[str, Any]]:
    """
    获取业务列表（带统计信息）

    异步绑定统计：先返回业务列表，统计信息通过后续API补全
    """
    biz_list = get_biz_list(supplier_account)
    return biz_list


def get_set_list_with_statistics(bk_biz_id: int,
                                 supplier_account: str = DEFAULT_SUPPLIER) -> List[Dict[str, Any]]:
    """
    获取业务下的集群列表（带统计信息）

    Args:
        bk_biz_id: 业务ID
        supplier_account: 供应商账号

    Returns:
        集群列表，包含 host_count
    """
    set_instances = _load_instances(MAINLINE_MODEL_SET, bk_biz_id, supplier_account)

    set_ids = [s[MODEL_ID_FIELD[MAINLINE_MODEL_SET]] for s in set_instances]
    if not set_ids:
        return set_instances

    placeholders = ', '.join([f":set_{i}" for i in range(len(set_ids))])
    params = {'bk_biz_id': bk_biz_id, 'supplier': supplier_account}
    for i, sid in enumerate(set_ids):
        params[f'set_{i}'] = sid

    count_sql = f"""
        SELECT bk_set_id, COUNT(DISTINCT bk_host_id) as host_count
        FROM cc_ModuleHostConfig
        WHERE bk_biz_id = :bk_biz_id
          AND bk_supplier_account = :supplier
          AND bk_set_id IN ({placeholders})
        GROUP BY bk_set_id
    """
    rows = query_all(count_sql, params)
    set_host_count = {row['bk_set_id']: row['host_count'] for row in rows}

    for s in set_instances:
        sid = s[MODEL_ID_FIELD[MAINLINE_MODEL_SET]]
        s['host_count'] = set_host_count.get(sid, 0)

    return set_instances


def get_module_list_with_statistics(bk_set_id: int, bk_biz_id: int,
                                    supplier_account: str = DEFAULT_SUPPLIER) -> List[Dict[str, Any]]:
    """
    获取集群下的模块列表（带统计信息）

    Args:
        bk_set_id: 集群ID
        bk_biz_id: 业务ID
        supplier_account: 供应商账号

    Returns:
        模块列表，包含 host_count
    """
    sql = f"""
        SELECT {MODEL_ID_FIELD[MAINLINE_MODEL_MODULE]},
               {MODEL_NAME_FIELD[MAINLINE_MODEL_MODULE]},
               bk_set_id, bk_biz_id, "default",
               bk_supplier_account,
               *
        FROM {MODEL_INSTANCE_TABLE[MAINLINE_MODEL_MODULE]}
        WHERE bk_supplier_account = :supplier
          AND bk_biz_id = :bk_biz_id
          AND bk_set_id = :bk_set_id
        ORDER BY "default", {MODEL_ID_FIELD[MAINLINE_MODEL_MODULE]}
    """
    module_instances = query_all(sql, {
        'supplier': supplier_account,
        'bk_biz_id': bk_biz_id,
        'bk_set_id': bk_set_id
    })

    if not module_instances:
        return module_instances

    module_ids = [m[MODEL_ID_FIELD[MAINLINE_MODEL_MODULE]] for m in module_instances]
    placeholders = ', '.join([f":mod_{i}" for i in range(len(module_ids))])
    params = {'supplier': supplier_account, 'bk_biz_id': bk_biz_id}
    for i, mid in enumerate(module_ids):
        params[f'mod_{i}'] = mid

    count_sql = f"""
        SELECT bk_module_id, COUNT(DISTINCT bk_host_id) as host_count
        FROM cc_ModuleHostConfig
        WHERE bk_biz_id = :bk_biz_id
          AND bk_supplier_account = :supplier
          AND bk_module_id IN ({placeholders})
        GROUP BY bk_module_id
    """
    rows = query_all(count_sql, params)
    module_host_count = {row['bk_module_id']: row['host_count'] for row in rows}

    for m in module_instances:
        mid = m[MODEL_ID_FIELD[MAINLINE_MODEL_MODULE]]
        m['host_count'] = module_host_count.get(mid, 0)

    return module_instances


def get_biz_host_count(bk_biz_id: int,
                       supplier_account: str = DEFAULT_SUPPLIER) -> int:
    """
    获取业务下主机总数（异步统计接口）

    Args:
        bk_biz_id: 业务ID
        supplier_account: 供应商账号

    Returns:
        主机总数
    """
    sql = """
        SELECT COUNT(DISTINCT bk_host_id) as cnt
        FROM cc_ModuleHostConfig
        WHERE bk_biz_id = :bk_biz_id
          AND bk_supplier_account = :supplier
    """
    row = query_one(sql, {'bk_biz_id': bk_biz_id, 'supplier': supplier_account})
    return row['cnt'] if row else 0


def get_set_host_count(bk_set_id: int, bk_biz_id: int,
                       supplier_account: str = DEFAULT_SUPPLIER) -> int:
    """
    获取集群下主机总数（异步统计接口）

    Args:
        bk_set_id: 集群ID
        bk_biz_id: 业务ID
        supplier_account: 供应商账号

    Returns:
        主机总数
    """
    sql = """
        SELECT COUNT(DISTINCT bk_host_id) as cnt
        FROM cc_ModuleHostConfig
        WHERE bk_set_id = :bk_set_id
          AND bk_biz_id = :bk_biz_id
          AND bk_supplier_account = :supplier
    """
    row = query_one(sql, {
        'bk_set_id': bk_set_id,
        'bk_biz_id': bk_biz_id,
        'supplier': supplier_account
    })
    return row['cnt'] if row else 0


def get_module_host_count(bk_module_id: int,
                          supplier_account: str = DEFAULT_SUPPLIER) -> int:
    """
    获取模块下主机总数（异步统计接口）

    Args:
        bk_module_id: 模块ID
        supplier_account: 供应商账号

    Returns:
        主机总数
    """
    sql = """
        SELECT COUNT(DISTINCT bk_host_id) as cnt
        FROM cc_ModuleHostConfig
        WHERE bk_module_id = :bk_module_id
          AND bk_supplier_account = :supplier
    """
    row = query_one(sql, {
        'bk_module_id': bk_module_id,
        'supplier': supplier_account
    })
    return row['cnt'] if row else 0


def get_biz_host_list(bk_biz_id: int, page: int = 1, page_size: int = 20,
                      sort: str = 'bk_host_id',
                      supplier_account: str = DEFAULT_SUPPLIER) -> Dict[str, Any]:
    """
    获取业务下的主机列表（分页）

    通过 cc_ModuleHostConfig 关联 cc_HostBase

    Args:
        bk_biz_id: 业务ID
        page: 页码
        page_size: 每页数量
        sort: 排序字段
        supplier_account: 供应商账号

    Returns:
        { info: [...], count: total }
    """
    count_sql = """
        SELECT COUNT(DISTINCT h.bk_host_id) as cnt
        FROM cc_HostBase h
        INNER JOIN cc_ModuleHostConfig mhc
            ON h.bk_host_id = mhc.bk_host_id
        WHERE mhc.bk_biz_id = :bk_biz_id
          AND h.bk_supplier_account = :supplier
          AND mhc.bk_supplier_account = :supplier
    """
    count_row = query_one(count_sql, {'bk_biz_id': bk_biz_id, 'supplier': supplier_account})
    total = count_row['cnt'] if count_row else 0

    offset = (page - 1) * page_size
    sort_field = 'h.bk_host_id' if sort == 'bk_host_id' else f'h.{sort}'
    sort_order = 'ASC'
    if sort.startswith('-'):
        sort_order = 'DESC'
        sort_field = f'h.{sort[1:]}'

    list_sql = f"""
        SELECT DISTINCT h.*
        FROM cc_HostBase h
        INNER JOIN cc_ModuleHostConfig mhc
            ON h.bk_host_id = mhc.bk_host_id
        WHERE mhc.bk_biz_id = :bk_biz_id
          AND h.bk_supplier_account = :supplier
          AND mhc.bk_supplier_account = :supplier
        ORDER BY {sort_field} {sort_order}
        LIMIT :page_size OFFSET :offset
    """
    rows = query_all(list_sql, {
        'bk_biz_id': bk_biz_id,
        'supplier': supplier_account,
        'page_size': page_size,
        'offset': offset
    })

    return {'info': rows, 'count': total}


def get_set_host_list(bk_set_id: int, bk_biz_id: int, page: int = 1, page_size: int = 20,
                      sort: str = 'bk_host_id',
                      supplier_account: str = DEFAULT_SUPPLIER) -> Dict[str, Any]:
    """
    获取集群下的主机列表（分页）

    Args:
        bk_set_id: 集群ID
        bk_biz_id: 业务ID
        page: 页码
        page_size: 每页数量
        sort: 排序字段
        supplier_account: 供应商账号

    Returns:
        { info: [...], count: total }
    """
    count_sql = """
        SELECT COUNT(DISTINCT h.bk_host_id) as cnt
        FROM cc_HostBase h
        INNER JOIN cc_ModuleHostConfig mhc
            ON h.bk_host_id = mhc.bk_host_id
        WHERE mhc.bk_set_id = :bk_set_id
          AND mhc.bk_biz_id = :bk_biz_id
          AND h.bk_supplier_account = :supplier
          AND mhc.bk_supplier_account = :supplier
    """
    count_row = query_one(count_sql, {
        'bk_set_id': bk_set_id,
        'bk_biz_id': bk_biz_id,
        'supplier': supplier_account
    })
    total = count_row['cnt'] if count_row else 0

    offset = (page - 1) * page_size
    sort_field = 'h.bk_host_id' if sort == 'bk_host_id' else f'h.{sort}'
    sort_order = 'ASC'
    if sort.startswith('-'):
        sort_order = 'DESC'
        sort_field = f'h.{sort[1:]}'

    list_sql = f"""
        SELECT DISTINCT h.*
        FROM cc_HostBase h
        INNER JOIN cc_ModuleHostConfig mhc
            ON h.bk_host_id = mhc.bk_host_id
        WHERE mhc.bk_set_id = :bk_set_id
          AND mhc.bk_biz_id = :bk_biz_id
          AND h.bk_supplier_account = :supplier
          AND mhc.bk_supplier_account = :supplier
        ORDER BY {sort_field} {sort_order}
        LIMIT :page_size OFFSET :offset
    """
    rows = query_all(list_sql, {
        'bk_set_id': bk_set_id,
        'bk_biz_id': bk_biz_id,
        'supplier': supplier_account,
        'page_size': page_size,
        'offset': offset
    })

    return {'info': rows, 'count': total}


def get_module_host_list(bk_module_id: int, page: int = 1, page_size: int = 20,
                         sort: str = 'bk_host_id',
                         supplier_account: str = DEFAULT_SUPPLIER) -> Dict[str, Any]:
    """
    获取模块下的主机列表（分页）

    Args:
        bk_module_id: 模块ID
        page: 页码
        page_size: 每页数量
        sort: 排序字段
        supplier_account: 供应商账号

    Returns:
        { info: [...], count: total }
    """
    count_sql = """
        SELECT COUNT(DISTINCT h.bk_host_id) as cnt
        FROM cc_HostBase h
        INNER JOIN cc_ModuleHostConfig mhc
            ON h.bk_host_id = mhc.bk_host_id
        WHERE mhc.bk_module_id = :bk_module_id
          AND h.bk_supplier_account = :supplier
          AND mhc.bk_supplier_account = :supplier
    """
    count_row = query_one(count_sql, {
        'bk_module_id': bk_module_id,
        'supplier': supplier_account
    })
    total = count_row['cnt'] if count_row else 0

    offset = (page - 1) * page_size
    sort_field = 'h.bk_host_id' if sort == 'bk_host_id' else f'h.{sort}'
    sort_order = 'ASC'
    if sort.startswith('-'):
        sort_order = 'DESC'
        sort_field = f'h.{sort[1:]}'

    list_sql = f"""
        SELECT DISTINCT h.*
        FROM cc_HostBase h
        INNER JOIN cc_ModuleHostConfig mhc
            ON h.bk_host_id = mhc.bk_host_id
        WHERE mhc.bk_module_id = :bk_module_id
          AND h.bk_supplier_account = :supplier
          AND mhc.bk_supplier_account = :supplier
        ORDER BY {sort_field} {sort_order}
        LIMIT :page_size OFFSET :offset
    """
    rows = query_all(list_sql, {
        'bk_module_id': bk_module_id,
        'supplier': supplier_account,
        'page_size': page_size,
        'offset': offset
    })

    return {'info': rows, 'count': total}


# 缓存 cc_HostBase 表真实列名（动态 PRAGMA 获取，支持自定义属性）
_HOST_BASE_COLUMNS = None

def _get_host_base_columns():
    global _HOST_BASE_COLUMNS
    if _HOST_BASE_COLUMNS is None:
        try:
            rows = query_all('PRAGMA table_info("cc_HostBase")')
            _HOST_BASE_COLUMNS = {row['name'] for row in rows}
        except Exception:
            _HOST_BASE_COLUMNS = {'bk_host_id'}
    return _HOST_BASE_COLUMNS


def search_hosts(params: Dict[str, Any],
                 supplier_account: str = DEFAULT_SUPPLIER) -> Dict[str, Any]:
    """
    主机搜索（与原项目 HostCommonSearch 一致）

    请求载荷结构：
    {
        "bk_biz_id": 2,
        "ip": {
            "data": ["192.168.1.1"],
            "exact": 1,
            "flag": "bk_host_innerip|bk_host_outerip"
        },
        "condition": [
            {
                "bk_obj_id": "host",
                "fields": [],
                "condition": [
                    {"field": "bk_host_name", "operator": "$regex", "value": "web"}
                ]
            },
            {
                "bk_obj_id": "set",
                "fields": [],
                "condition": [
                    {"field": "bk_set_id", "operator": "$eq", "value": 10}
                ]
            },
            {
                "bk_obj_id": "module",
                "fields": [],
                "condition": [
                    {"field": "bk_module_id", "operator": "$in", "value": [100, 101]}
                ]
            }
        ],
        "page": {
            "start": 0,
            "limit": 20,
            "sort": "bk_host_id"
        }
    }

    对应原项目 logics/hostsearch.go 的 SearchHost 逻辑：
    1. ParseCondition: 按 bk_obj_id 归类条件到 host/set/module
    2. 拓扑条件层层递进: biz → set → module → hostIDs (通过 cc_ModuleHostConfig)
    3. 主机属性条件: 转换 ConditionItem 为 SQL WHERE
    4. IP 条件: 精确匹配用 IN，模糊匹配用 LIKE
    5. 组合查询: 拓扑 hostIDs AND 主机属性条件 AND IP 条件

    Args:
        params: HostCommonSearch 请求载荷
        supplier_account: 供应商账号

    Returns:
        { info: [...], count: total }
    """
    bk_biz_id = params.get('bk_biz_id')
    ip_info = params.get('ip', {})
    conditions = params.get('condition', [])
    page_info = params.get('page', {})

    # 解析分页参数
    start = int(page_info.get('start', 0))
    limit = int(page_info.get('limit', 20))
    sort = page_info.get('sort', 'bk_host_id')

    # 限制 limit 范围
    if limit <= 0:
        limit = 20
    if limit > 1000:
        limit = 1000
    if start < 0:
        start = 0
    offset = start

    # 解析排序: "field" 或 "field:1"(asc) 或 "field:-1"(desc) 或 "-field"(desc)
    sort_field = 'bk_host_id'
    sort_order = 'ASC'
    if sort:
        if sort.startswith('-'):
            sort_field = sort[1:]
            sort_order = 'DESC'
        elif ':' in sort:
            parts = sort.split(':')
            sort_field = parts[0]
            sort_order = 'DESC' if parts[1] == '-1' else 'ASC'
        else:
            sort_field = sort

    # ========== 步骤1: 按 bk_obj_id 归类条件 ==========
    host_cond_items = []    # host 对象的条件项
    set_cond_items = []     # set 对象的条件项
    module_cond_items = []  # module 对象的条件项

    for cond in conditions:
        obj_id = cond.get('bk_obj_id', '')
        cond_items = cond.get('condition', [])

        if obj_id == 'host':
            host_cond_items.extend(cond_items)
        elif obj_id == 'set':
            set_cond_items.extend(cond_items)
        elif obj_id == 'module':
            module_cond_items.extend(cond_items)

    # ========== 步骤2: 拓扑条件层层递进，获取 hostIDs ==========
    topo_host_ids = None
    topo_where = []
    topo_params = {'supplier': supplier_account}

    if bk_biz_id:
        topo_where.append('bk_biz_id = :bk_biz_id')
        topo_params['bk_biz_id'] = bk_biz_id

    # set 条件过滤：先查 cc_SetBase 获取符合的 bk_set_id
    if set_cond_items:
        set_ids = _filter_topo_ids('set', set_cond_items, bk_biz_id, supplier_account)
        if set_ids is not None:
            if not set_ids:
                return {'info': [], 'count': 0}
            placeholders = ', '.join([f":sid_{i}" for i in range(len(set_ids))])
            topo_where.append(f'bk_set_id IN ({placeholders})')
            for i, sid in enumerate(set_ids):
                topo_params[f'sid_{i}'] = sid

    # module 条件过滤：先查 cc_ModuleBase 获取符合的 bk_module_id
    if module_cond_items:
        module_ids = _filter_topo_ids('module', module_cond_items, bk_biz_id, supplier_account)
        if module_ids is not None:
            if not module_ids:
                return {'info': [], 'count': 0}
            placeholders = ', '.join([f":mid_{i}" for i in range(len(module_ids))])
            topo_where.append(f'bk_module_id IN ({placeholders})')
            for i, mid in enumerate(module_ids):
                topo_params[f'mid_{i}'] = mid

    # 查询 cc_ModuleHostConfig 获取符合拓扑条件的 hostIDs
    if topo_where:
        topo_sql = f"""
            SELECT DISTINCT bk_host_id
            FROM cc_ModuleHostConfig
            WHERE {' AND '.join(topo_where)}
        """
        topo_rows = query_all(topo_sql, topo_params)
        topo_host_ids = [row['bk_host_id'] for row in topo_rows]
        if not topo_host_ids:
            return {'info': [], 'count': 0}

    # ========== 步骤3: 构建主机属性条件 ==========
    host_where = []
    host_params = {}
    param_idx = 0

    for item in host_cond_items:
        field = item.get('field')
        operator = item.get('operator', '$eq')
        value = item.get('value')

        if not field:
            continue

        sql_cond, sql_params = _build_condition_sql(field, operator, value, param_idx)
        if sql_cond:
            host_where.append(sql_cond)
            host_params.update(sql_params)
            param_idx += len(sql_params)

    # ========== 步骤4: 构建 IP 条件 ==========
    ip_data = ip_info.get('data', [])
    ip_exact = ip_info.get('exact', 0)
    ip_flag = ip_info.get('flag', 'bk_host_innerip|bk_host_outerip')
    if isinstance(ip_flag, list):
        ip_flag = '|'.join(ip_flag)

    if ip_data:
        ip_cond, ip_params = _build_ip_condition(ip_data, ip_exact, ip_flag, param_idx)
        if ip_cond:
            host_where.append(ip_cond)
            host_params.update(ip_params)

    # ========== 步骤5: 组合查询 ==========
    where_clauses = ['h.bk_supplier_account = :supplier']
    query_params = {'supplier': supplier_account}

    # 拓扑条件：hostIDs 过滤
    if topo_host_ids is not None:
        if not topo_host_ids:
            return {'info': [], 'count': 0}
        placeholders = ', '.join([f":hid_{i}" for i in range(len(topo_host_ids))])
        where_clauses.append(f'h.bk_host_id IN ({placeholders})')
        for i, hid in enumerate(topo_host_ids):
            query_params[f'hid_{i}'] = hid

    # 主机属性条件 + IP 条件
    for cond in host_where:
        where_clauses.append(cond)

    # 合并 host_params
    for k, v in host_params.items():
        if k != 'supplier':
            query_params[k] = v

    where_sql = ' AND '.join(where_clauses)

    # 排序字段安全处理（动态校验，替代硬编码白名单）
    # 校验规则：
    #   1. 字段名必须是合法小写标识符（^[a-z][a-z0-9_]*$，防注入）
    #   2. 字段必须是 cc_HostBase 真实存在的列（从 PRAGMA table_info 动态获取，支持自定义属性）
    # 不满足任一条件即回退到 bk_host_id ASC
    if not isinstance(sort_field, str) or not __import__('re').fullmatch(r'[a-z][a-z0-9_]*', sort_field):
        sort_field = 'bk_host_id'
        sort_order = 'ASC'
    else:
        host_columns = _get_host_base_columns()
        if sort_field not in host_columns:
            sort_field = 'bk_host_id'
            sort_order = 'ASC'

    # 查询总数
    count_sql = f"""
        SELECT COUNT(DISTINCT h.bk_host_id) as cnt
        FROM cc_HostBase h
        WHERE {where_sql}
    """
    count_row = query_one(count_sql, query_params)
    total = count_row['cnt'] if count_row else 0

    # 查询列表
    list_sql = f"""
        SELECT DISTINCT h.*
        FROM cc_HostBase h
        WHERE {where_sql}
        ORDER BY h.{sort_field} {sort_order}
        LIMIT :limit_val OFFSET :offset_val
    """
    query_params['limit_val'] = limit
    query_params['offset_val'] = offset

    rows = query_all(list_sql, query_params)

    # 复刻原项目 logics/hostsearch.go 的 fillHostSetInfo / fillHostModuleInfo：
    # 搜索主机后，按 cc_ModuleHostConfig 查出每个主机所属的集群(set)/模块(module)，
    # 批量拉取 set/module 名称，内嵌 set[]/module[] 到每个 host，
    # 供前端业务拓扑主机列表的“集群名称/模块名称”列聚合展示。
    # 对应原项目 SearchHost 第 6 步：获取主机拓扑(set/module)信息并填充。
    _enrich_hosts_with_topo(rows, bk_biz_id, supplier_account)

    return {'info': rows, 'count': total}


def _enrich_hosts_with_topo(rows: List[Dict[str, Any]],
                            bk_biz_id: Optional[int],
                            supplier_account: str = DEFAULT_SUPPLIER) -> None:
    """
    给主机列表结果中的每个主机内嵌其所属集群(set)/模块(module) 聚合信息。

    对齐原项目 src/scene_server/host_server/logics/hostsearch.go：
      - fillHostSetInfo:   host["set"]    = [{bk_set_id, bk_set_name, TopoModuleName, ...}]
      - fillHostModuleInfo: host["module"] = [{bk_module_id, bk_module_name, TopoModuleName, ...}]
      - TopoModuleName 路径分隔符与原项目一致为 "##"（common.SplitFlag / host.go SplitFlag="##"）

    数据来源（lite 对应表）：
      - cc_ModuleHostConfig: 主机-模块绑定（bk_host_id, bk_set_id, bk_module_id）
      - cc_SetBase:          集群名称等属性
      - cc_ModuleBase:       模块名称等属性
      - cc_ApplicationBase:  业务名称（拓扑路径前缀）

    Args:
        rows: search_hosts 查询出的主机实例列表（原地修改，附加 set/module 字段）
        bk_biz_id: 业务ID（拓扑路径前缀 + 绑定过滤）
        supplier_account: 供应商账号
    """
    # 空结果直接返回，避免无谓查询
    if not rows:
        return

    host_ids = [r.get('bk_host_id') for r in rows if r.get('bk_host_id') is not None]
    if not host_ids:
        for r in rows:
            r['set'] = []
            r['module'] = []
        return

    # ========== 1. 查 cc_ModuleHostConfig 获取每个主机的 set/module 绑定 ==========
    rel_params = {'supplier': supplier_account, 'biz': bk_biz_id}
    rel_ph = ', '.join([f':hid_{i}' for i in range(len(host_ids))])
    for i, hid in enumerate(host_ids):
        rel_params[f'hid_{i}'] = hid

    rel_sql = f"""
        SELECT bk_host_id, bk_set_id, bk_module_id
        FROM cc_ModuleHostConfig
        WHERE bk_supplier_account = :supplier
          AND bk_biz_id = :biz
          AND bk_host_id IN ({rel_ph})
    """
    rel_rows = query_all(rel_sql, rel_params)

    host_bindings: Dict[int, List[tuple]] = {hid: [] for hid in host_ids}
    set_ids: set = set()
    module_ids: set = set()
    for rel in rel_rows:
        hid = rel['bk_host_id']
        sid = rel['bk_set_id']
        mid = rel['bk_module_id']
        host_bindings[hid].append((sid, mid))
        if sid:
            set_ids.add(sid)
        if mid:
            module_ids.add(mid)

    # ========== 2. 批量拉取 set / module 详情 ==========
    set_info_map: Dict[int, Dict[str, Any]] = {}
    if set_ids:
        s_params = {'supplier': supplier_account}
        s_ph = ', '.join([f':sid_{i}' for i in range(len(set_ids))])
        for i, sid in enumerate(set_ids):
            s_params[f'sid_{i}'] = sid
        set_rows = query_all(
            f"SELECT * FROM cc_SetBase "
            f"WHERE bk_supplier_account = :supplier AND bk_set_id IN ({s_ph})",
            s_params
        )
        for s in set_rows:
            set_info_map[s['bk_set_id']] = dict(s)

    module_info_map: Dict[int, Dict[str, Any]] = {}
    if module_ids:
        m_params = {'supplier': supplier_account}
        m_ph = ', '.join([f':mid_{i}' for i in range(len(module_ids))])
        for i, mid in enumerate(module_ids):
            m_params[f'mid_{i}'] = mid
        module_rows = query_all(
            f"SELECT * FROM cc_ModuleBase "
            f"WHERE bk_supplier_account = :supplier AND bk_module_id IN ({m_ph})",
            m_params
        )
        for m in module_rows:
            module_info_map[m['bk_module_id']] = dict(m)

    # ========== 3. 业务名称（拓扑路径前缀） ==========
    biz_name = ''
    if bk_biz_id:
        biz_row = query_one(
            "SELECT bk_biz_name FROM cc_ApplicationBase "
            "WHERE bk_supplier_account = :supplier AND bk_biz_id = :biz",
            {'supplier': supplier_account, 'biz': bk_biz_id}
        )
        biz_name = biz_row['bk_biz_name'] if biz_row else ''

    SPLIT = '##'  # 对齐原项目 common.SplitFlag / host.go SplitFlag = "##"

    # ========== 4. 组装：去重后内嵌到每个主机 ==========
    for r in rows:
        hid = r.get('bk_host_id')
        bindings = host_bindings.get(hid, [])
        set_arr: List[Dict[str, Any]] = []
        module_arr: List[Dict[str, Any]] = []
        seen_sets: set = set()
        seen_modules: set = set()

        for (sid, mid) in bindings:
            # 集群信息
            if sid and sid not in seen_sets and sid in set_info_map:
                seen_sets.add(sid)
                s_info = dict(set_info_map[sid])
                s_name = s_info.get('bk_set_name', '')
                s_info['TopoModuleName'] = f"{biz_name}{SPLIT}{s_name}"
                set_arr.append(s_info)

            # 模块信息（拓扑路径需带上其所属集群名称）
            if mid and mid not in seen_modules and mid in module_info_map:
                seen_modules.add(mid)
                m_info = dict(module_info_map[mid])
                m_name = m_info.get('bk_module_name', '')
                s_name_for_path = set_info_map.get(sid, {}).get('bk_set_name', '') if sid else ''
                m_info['TopoModuleName'] = f"{biz_name}{SPLIT}{s_name_for_path}{SPLIT}{m_name}"
                module_arr.append(m_info)

        r['set'] = set_arr
        r['module'] = module_arr


def _filter_topo_ids(model_id: str, cond_items: list, bk_biz_id: int,
                     supplier_account: str = DEFAULT_SUPPLIER):
    """
    根据拓扑条件查询符合的实例ID列表

    Args:
        model_id: 模型ID（set/module）
        cond_items: 条件项列表 [{field, operator, value}]
        bk_biz_id: 业务ID
        supplier_account: 供应商账号

    Returns:
        list: 符合条件的实例ID列表，None 表示无条件
    """
    if not cond_items:
        return None

    table = MODEL_INSTANCE_TABLE.get(model_id)
    id_field = MODEL_ID_FIELD.get(model_id)
    if not table or not id_field:
        return None

    where_clauses = ['bk_supplier_account = :supplier']
    params = {'supplier': supplier_account}

    if bk_biz_id:
        where_clauses.append('bk_biz_id = :bk_biz_id')
        params['bk_biz_id'] = bk_biz_id

    param_idx = 0
    for item in cond_items:
        field = item.get('field')
        operator = item.get('operator', '$eq')
        value = item.get('value')

        if not field:
            continue

        sql_cond, sql_params = _build_condition_sql(field, operator, value, param_idx)
        if sql_cond:
            where_clauses.append(sql_cond)
            params.update(sql_params)
            param_idx += len(sql_params)

    where_sql = ' AND '.join(where_clauses)
    sql = f"""
        SELECT {id_field}
        FROM {table}
        WHERE {where_sql}
    """
    rows = query_all(sql, params)
    return [row[id_field] for row in rows]


def _build_condition_sql(field: str, operator: str, value: Any,
                         param_idx: int) -> tuple:
    """
    将 ConditionItem 转换为 SQL WHERE 子句

    对应原项目 paraparse/host.go 的 ParseHostParams 与 pkg/filter 的 operator 实现，
    模糊匹配的大小写语义与原项目严格保持一致：

    操作符          原项目路径                          MongoDB 表达                          大小写
    $regex          ParseHostParams(BKDBLIKE)        {field: {$regex: value}}              敏感
    $contains_s     filter.ContainsSensitiveOp       {field: {$regex: value}}              敏感
    contains        ParseHostParams(filter.Contains) {field: {$regex: value, $options:"i"}} 不敏感
    $contains       filter.ContainsOp(前端别名)       {field: {$regex: value, $options:"i"}} 不敏感

    Args:
        field: 字段名
        operator: 操作符（$eq/$ne/$in/$nin/$regex/$contains/$contains_s/contains ...）
        value: 比较值
        param_idx: 参数索引（避免重名）

    Returns:
        (sql_clause, params_dict)
    """
    import re
    # 安全字段名（只允许字母数字下划线）
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', field):
        return ('', {})

    p_name = f'p_{param_idx}'

    if operator == '$eq':
        return (f'{field} = :{p_name}', {p_name: value})

    if operator == '$ne':
        return (f'{field} != :{p_name}', {p_name: value})

    if operator == '$in':
        if not isinstance(value, list) or not value:
            return ('1=0', {})
        placeholders = ', '.join([f':{p_name}_{i}' for i in range(len(value))])
        params = {f'{p_name}_{i}': v for i, v in enumerate(value)}
        return (f'{field} IN ({placeholders})', params)

    if operator == '$nin':
        if not isinstance(value, list) or not value:
            return ('', {})
        placeholders = ', '.join([f':{p_name}_{i}' for i in range(len(value))])
        params = {f'{p_name}_{i}': v for i, v in enumerate(value)}
        return (f'{field} NOT IN ({placeholders})', params)

    # 模糊匹配（子串包含），大小写语义严格对齐原项目 bk-cmdb
    #   $regex / $contains_s -> 大小写敏感（MongoDB 默认 $regex 不带 $options:"i"）
    #   contains / $contains -> 大小写不敏感（MongoDB $regex 带 $options:"i"）
    if operator in ('$regex', '$contains_s'):
        # 大小写敏感子串匹配：INSTR 在 SQLite 中为大小写敏感
        return (f'INSTR({field}, :{p_name}) > 0', {p_name: value})

    if operator in ('$contains', 'contains'):
        # 大小写不敏感子串匹配：LOWER 两侧保证与 MongoDB $options:"i" 等价
        return (f'LOWER({field}) LIKE LOWER(:{p_name})', {p_name: f'%{value}%'})

    if operator in ('$gt', '$lt', '$gte', '$lte'):
        op_map = {'$gt': '>', '$lt': '<', '$gte': '>=', '$lte': '<='}
        sql_op = op_map[operator]
        return (f'{field} {sql_op} :{p_name}', {p_name: value})

    if operator == '$range':
        # $range: value 为 [start, end]，生成 field >= start AND field <= end
        if isinstance(value, list) and len(value) >= 2:
            p1 = f'{p_name}_0'
            p2 = f'{p_name}_1'
            return (f'({field} >= :{p1} AND {field} <= :{p2})',
                    {p1: value[0], p2: value[1]})
        elif isinstance(value, list) and len(value) == 1:
            return (f'{field} >= :{p_name}', {p_name: value[0]})

    # 默认 $eq
    return (f'{field} = :{p_name}', {p_name: value})


def _build_ip_condition(ip_data: list, ip_exact: int, ip_flag: str,
                        param_idx: int) -> tuple:
    """
    构建 IP 搜索条件

    对应原项目 paraparse/host.go 的 ParseHostIPParams

    Args:
        ip_data: IP 列表（支持 "cloudID:ip" 格式）
        ip_exact: 1=精确匹配，其他=模糊匹配
        ip_flag: 搜索字段标识（bk_host_innerip / bk_host_outerip / 两者组合）
        param_idx: 参数索引

    Returns:
        (sql_clause, params_dict)
    """
    if not ip_data:
        return ('', {})

    # 解析 flag，确定搜索哪些字段
    flags = ip_flag.split('|') if ip_flag else ['bk_host_innerip']
    search_fields = []
    for f in flags:
        f = f.strip()
        if f in ('bk_host_innerip', 'bk_host_outerip'):
            search_fields.append(f)

    if not search_fields:
        search_fields = ['bk_host_innerip']

    # 解析 IP 数据，分离 cloudID:ip 格式
    plain_ips = []
    cloud_ip_pairs = []
    for item in ip_data:
        if ':' in str(item):
            parts = str(item).split(':', 1)
            try:
                cloud_id = int(parts[0])
                cloud_ip_pairs.append((cloud_id, parts[1]))
            except ValueError:
                plain_ips.append(str(item))
        else:
            plain_ips.append(str(item))

    conditions = []
    params = {}
    idx = param_idx

    if ip_exact == 1:
        # 精确匹配：使用 IN
        for field in search_fields:
            if plain_ips:
                placeholders = ', '.join([f':ip_{idx}_{i}' for i in range(len(plain_ips))])
                for i, ip in enumerate(plain_ips):
                    params[f'ip_{idx}_{i}'] = ip
                conditions.append(f'{field} IN ({placeholders})')
                idx += len(plain_ips)

            if cloud_ip_pairs:
                cloud_placeholders = ', '.join([f':cip_{idx}_{i}' for i in range(len(cloud_ip_pairs))])
                for i, (cid, ip) in enumerate(cloud_ip_pairs):
                    params[f'cip_{idx}_{i}'] = ip
                cloud_ids = ', '.join([str(c) for c, _ in cloud_ip_pairs])
                conditions.append(f'(bk_cloud_id IN ({cloud_ids}) AND {field} IN ({cloud_placeholders}))')
                idx += len(cloud_ip_pairs)
    else:
        # 模糊匹配：使用 LIKE，多个 IP 用 OR 连接
        for field in search_fields:
            for ip in plain_ips:
                p_name = f'ip_{idx}'
                params[p_name] = f'%{ip}%'
                conditions.append(f'{field} LIKE :{p_name}')
                idx += 1

    if not conditions:
        return ('', {})

    if len(conditions) > 1:
        return ('(' + ' OR '.join(conditions) + ')', params)
    return (conditions[0], params)


def get_host_topology(bk_host_id: int, bk_biz_id: int = None,
                      supplier_account: str = DEFAULT_SUPPLIER) -> List[Dict[str, Any]]:
    """
    获取主机的业务拓扑信息（业务 -> 集群 -> 模块）

    Args:
        bk_host_id: 主机ID
        bk_biz_id: 业务ID（可选，不传则返回所有业务）
        supplier_account: 供应商账号

    Returns:
        [
            {
                bk_biz_id: 1,
                bk_biz_name: '业务1',
                sets: [
                    {
                        bk_set_id: 1,
                        bk_set_name: '集群1',
                        modules: [
                            { bk_module_id: 1, bk_module_name: '模块1' },
                            ...
                        ]
                    },
                    ...
                ]
            },
            ...
        ]
    """
    params = {
        'host_id': bk_host_id,
        'supplier': supplier_account
    }

    where_clause = """
        WHERE mhc.bk_host_id = :host_id
          AND mhc.bk_supplier_account = :supplier
          AND biz.bk_supplier_account = :supplier
          AND s.bk_supplier_account = :supplier
          AND m.bk_supplier_account = :supplier
    """

    if bk_biz_id:
        where_clause += " AND mhc.bk_biz_id = :biz_id"
        params['biz_id'] = bk_biz_id

    sql = f"""
        SELECT
            biz.bk_biz_id,
            biz.bk_biz_name,
            s.bk_set_id,
            s.bk_set_name,
            m.bk_module_id,
            m.bk_module_name
        FROM cc_ModuleHostConfig mhc
        INNER JOIN cc_ApplicationBase biz
            ON mhc.bk_biz_id = biz.bk_biz_id
        INNER JOIN cc_SetBase s
            ON mhc.bk_set_id = s.bk_set_id
            AND mhc.bk_biz_id = s.bk_biz_id
        INNER JOIN cc_ModuleBase m
            ON mhc.bk_module_id = m.bk_module_id
            AND mhc.bk_set_id = m.bk_set_id
            AND mhc.bk_biz_id = m.bk_biz_id
        {where_clause}
        ORDER BY biz.bk_biz_id, s.bk_set_id, m.bk_module_id
    """

    rows = query_all(sql, params)

    biz_map = {}
    for row in rows:
        biz_id = row['bk_biz_id']
        set_id = row['bk_set_id']
        module_id = row['bk_module_id']

        if biz_id not in biz_map:
            biz_map[biz_id] = {
                'bk_biz_id': biz_id,
                'bk_biz_name': row['bk_biz_name'],
                'sets': {}
            }

        if set_id not in biz_map[biz_id]['sets']:
            biz_map[biz_id]['sets'][set_id] = {
                'bk_set_id': set_id,
                'bk_set_name': row['bk_set_name'],
                'modules': []
            }

        biz_map[biz_id]['sets'][set_id]['modules'].append({
            'bk_module_id': module_id,
            'bk_module_name': row['bk_module_name']
        })

    result = []
    for biz_id in sorted(biz_map.keys()):
        biz = biz_map[biz_id]
        biz['sets'] = [biz['sets'][sid] for sid in sorted(biz['sets'].keys())]
        result.append(biz)

    return result


def create_set(bk_biz_id: int, names: List[str],
               supplier_account: str = DEFAULT_SUPPLIER) -> Dict[str, Any]:
    """
    创建集群（批量）

    Args:
        bk_biz_id: 业务ID
        names: 集群名称列表
        supplier_account: 供应商账号

    Returns:
        { 'created': [...], 'error_names': [...] }
    """
    from app.db.executor import SQLExecutor
    import time

    executor = SQLExecutor()
    created = []
    error_names = []

    # 验证业务是否存在
    biz = query_one("""
        SELECT bk_biz_id FROM cc_ApplicationBase
        WHERE bk_biz_id = :biz_id AND bk_supplier_account = :supplier
    """, {'biz_id': bk_biz_id, 'supplier': supplier_account})

    if not biz:
        raise ValueError(f'业务 {bk_biz_id} 不存在')

    # 获取当前最大集群ID
    max_id_row = query_one("""
        SELECT MAX(bk_set_id) as max_id FROM cc_SetBase
    """, {})
    next_id = (max_id_row['max_id'] or 0) + 1

    # 过滤空名称和去重
    unique_names = []
    for name in names:
        name = name.strip()
        if name and name not in unique_names:
            unique_names.append(name)

    current_time = time.strftime('%Y-%m-%d %H:%M:%S')

    for name in unique_names:
        try:
            # 插入集群数据
            executor.execute("""
                INSERT INTO cc_SetBase
                (bk_set_id, bk_set_name, bk_parent_id, bk_biz_id, "default",
                 bk_supplier_account, create_time, last_time, creator, modifier)
                VALUES
                (:bk_set_id, :bk_set_name, :bk_parent_id, :bk_biz_id, :default,
                 :bk_supplier_account, :create_time, :last_time, :creator, :modifier)
            """, {
                'bk_set_id': next_id,
                'bk_set_name': name,
                'bk_parent_id': bk_biz_id,
                'bk_biz_id': bk_biz_id,
                'default': 0,
                'bk_supplier_account': supplier_account,
                'create_time': current_time,
                'last_time': current_time,
                'creator': 'admin',
                'modifier': 'admin'
            })

            created.append({
                'bk_set_id': next_id,
                'bk_set_name': name,
                'bk_biz_id': bk_biz_id
            })
            next_id += 1
        except Exception as e:
            error_names.append({
                'name': name,
                'error': str(e)
            })

    return {
        'created': created,
        'error_names': error_names
    }


def create_module(bk_set_id: int, names: List[str],
                  bk_biz_id: int = None, supplier_account: str = DEFAULT_SUPPLIER) -> Dict[str, Any]:
    """
    创建模块（批量）

    Args:
        bk_set_id: 集群ID
        names: 模块名称列表
        bk_biz_id: 业务ID（可选，会从集群表查询）
        supplier_account: 供应商账号

    Returns:
        { 'created': [...], 'error_names': [...] }
    """
    from app.db.executor import SQLExecutor
    import time

    executor = SQLExecutor()
    created = []
    error_names = []

    # 查询集群信息
    set_info = query_one("""
        SELECT bk_set_id, bk_biz_id, bk_set_name FROM cc_SetBase
        WHERE bk_set_id = :set_id AND bk_supplier_account = :supplier
    """, {'set_id': bk_set_id, 'supplier': supplier_account})

    if not set_info:
        raise ValueError(f'集群 {bk_set_id} 不存在')

    # 使用集群的业务ID
    if not bk_biz_id:
        bk_biz_id = set_info['bk_biz_id']

    # 获取当前最大模块ID
    max_id_row = query_one("""
        SELECT MAX(bk_module_id) as max_id FROM cc_ModuleBase
    """, {})
    next_id = (max_id_row['max_id'] or 0) + 1

    # 过滤空名称和去重
    unique_names = []
    for name in names:
        name = name.strip()
        if name and name not in unique_names:
            unique_names.append(name)

    current_time = time.strftime('%Y-%m-%d %H:%M:%S')

    for name in unique_names:
        try:
            # 插入模块数据
            executor.execute("""
                INSERT INTO cc_ModuleBase
                (bk_module_id, bk_module_name, bk_parent_id, bk_set_id, bk_biz_id,
                 "default", bk_supplier_account, create_time, last_time, creator, modifier)
                VALUES
                (:bk_module_id, :bk_module_name, :bk_parent_id, :bk_set_id, :bk_biz_id,
                 :default, :bk_supplier_account, :create_time, :last_time, :creator, :modifier)
            """, {
                'bk_module_id': next_id,
                'bk_module_name': name,
                'bk_parent_id': bk_set_id,
                'bk_set_id': bk_set_id,
                'bk_biz_id': bk_biz_id,
                'default': 0,
                'bk_supplier_account': supplier_account,
                'create_time': current_time,
                'last_time': current_time,
                'creator': 'admin',
                'modifier': 'admin'
            })

            created.append({
                'bk_module_id': next_id,
                'bk_module_name': name,
                'bk_set_id': bk_set_id,
                'bk_biz_id': bk_biz_id
            })
            next_id += 1
        except Exception as e:
            error_names.append({
                'name': name,
                'error': str(e)
            })

    return {
        'created': created,
        'error_names': error_names
    }


def get_node_detail(bk_obj_id: str, bk_inst_id: int,
                    bk_biz_id: int = None, supplier_account: str = DEFAULT_SUPPLIER) -> Dict[str, Any]:
    """
    获取节点详情（biz/set/module）

    Args:
        bk_obj_id: 节点类型
        bk_inst_id: 节点实例ID
        bk_biz_id: 业务ID（set/module时必填）
        supplier_account: 供应商账号

    Returns:
        节点详情字典
    """
    if bk_obj_id == 'biz':
        result = query_one("""
            SELECT bk_biz_id, bk_biz_name, "default", bk_supplier_account,
                   create_time, last_time, creator, modifier
            FROM cc_ApplicationBase
            WHERE bk_biz_id = :biz_id AND bk_supplier_account = :supplier
        """, {'biz_id': bk_inst_id, 'supplier': supplier_account})
    elif bk_obj_id == 'set':
        if not bk_biz_id:
            raise ValueError('获取集群详情需要 bk_biz_id')
        result = query_one("""
            SELECT bk_set_id, bk_set_name, bk_parent_id, bk_biz_id,
                   "default", bk_set_desc, bk_set_env, bk_service_status,
                   bk_supplier_account, create_time, last_time, creator, modifier
            FROM cc_SetBase
            WHERE bk_set_id = :set_id AND bk_biz_id = :biz_id AND bk_supplier_account = :supplier
        """, {'set_id': bk_inst_id, 'biz_id': bk_biz_id, 'supplier': supplier_account})
    elif bk_obj_id == 'module':
        if not bk_biz_id:
            raise ValueError('获取模块详情需要 bk_biz_id')
        result = query_one("""
            SELECT bk_module_id, bk_module_name, bk_parent_id, bk_set_id, bk_biz_id,
                   "default", bk_supplier_account, create_time, last_time, creator, modifier
            FROM cc_ModuleBase
            WHERE bk_module_id = :module_id AND bk_biz_id = :biz_id AND bk_supplier_account = :supplier
        """, {'module_id': bk_inst_id, 'biz_id': bk_biz_id, 'supplier': supplier_account})
    else:
        raise ValueError(f'不支持的节点类型: {bk_obj_id}')

    if not result:
        raise ValueError(f'{bk_obj_id} 节点 {bk_inst_id} 不存在')

    return dict(result)


def update_node(bk_obj_id: str, bk_inst_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新节点信息（biz/set/module）

    Args:
        bk_obj_id: 节点类型
        bk_inst_id: 节点实例ID
        params: 更新参数

    Returns:
        更新后的节点信息
    """
    from app.db.executor import SQLExecutor
    import time

    executor = SQLExecutor()
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')

    if bk_obj_id == 'biz':
        bk_biz_name = params.get('bk_biz_name')
        if not bk_biz_name:
            raise ValueError('业务名称不能为空')
        executor.execute("""
            UPDATE cc_ApplicationBase
            SET bk_biz_name = :bk_biz_name, last_time = :last_time, modifier = :modifier
            WHERE bk_biz_id = :bk_inst_id
        """, {
            'bk_biz_name': bk_biz_name,
            'last_time': current_time,
            'modifier': 'admin',
            'bk_inst_id': bk_inst_id
        })
    elif bk_obj_id == 'set':
        bk_set_name = params.get('bk_set_name')
        if not bk_set_name:
            raise ValueError('集群名称不能为空')
        executor.execute("""
            UPDATE cc_SetBase
            SET bk_set_name = :bk_set_name,
                bk_set_desc = :bk_set_desc,
                bk_set_env = :bk_set_env,
                bk_service_status = :bk_service_status,
                last_time = :last_time,
                modifier = :modifier
            WHERE bk_set_id = :bk_inst_id
        """, {
            'bk_set_name': bk_set_name,
            'bk_set_desc': params.get('bk_set_desc', ''),
            'bk_set_env': params.get('bk_set_env', '3'),
            'bk_service_status': params.get('bk_service_status', '1'),
            'last_time': current_time,
            'modifier': 'admin',
            'bk_inst_id': bk_inst_id
        })
    elif bk_obj_id == 'module':
        bk_module_name = params.get('bk_module_name')
        if not bk_module_name:
            raise ValueError('模块名称不能为空')
        executor.execute("""
            UPDATE cc_ModuleBase
            SET bk_module_name = :bk_module_name,
                last_time = :last_time,
                modifier = :modifier
            WHERE bk_module_id = :bk_inst_id
        """, {
            'bk_module_name': bk_module_name,
            'last_time': current_time,
            'modifier': 'admin',
            'bk_inst_id': bk_inst_id
        })
    else:
        raise ValueError(f'不支持的节点类型: {bk_obj_id}')

    return {'bk_inst_id': bk_inst_id}


def delete_node(bk_obj_id: str, bk_inst_id: int,
                bk_biz_id: int = None, supplier_account: str = DEFAULT_SUPPLIER) -> None:
    """
    删除节点（biz/set/module）

    Args:
        bk_obj_id: 节点类型
        bk_inst_id: 节点实例ID
        bk_biz_id: 业务ID（set/module时必填）
        supplier_account: 供应商账号
    """
    from app.db.executor import SQLExecutor

    executor = SQLExecutor()

    if bk_obj_id == 'biz':
        # 检查业务下是否有集群
        set_count = query_one("""
            SELECT COUNT(*) as count FROM cc_SetBase WHERE bk_biz_id = :biz_id
        """, {'biz_id': bk_inst_id})
        if set_count and set_count['count'] > 0:
            raise ValueError('业务下存在集群，无法删除')

        executor.execute("""
            DELETE FROM cc_ApplicationBase WHERE bk_biz_id = :biz_id
        """, {'biz_id': bk_inst_id})
    elif bk_obj_id == 'set':
        if not bk_biz_id:
            raise ValueError('删除集群需要 bk_biz_id')

        # 复刻原项目：检查集群下的模块是否有关联主机
        # 先获取集群下所有模块ID
        module_ids = query_all("""
            SELECT bk_module_id FROM cc_ModuleBase WHERE bk_set_id = :set_id AND bk_biz_id = :biz_id
        """, {'set_id': bk_inst_id, 'biz_id': bk_biz_id})

        if module_ids:
            module_id_list = [str(m['bk_module_id']) for m in module_ids]
            placeholders = ','.join(module_id_list)
            # 检查这些模块是否有主机关联（cc_ModuleHostConfig）
            host_count_sql = f"""
                SELECT COUNT(DISTINCT bk_host_id) as count FROM cc_ModuleHostConfig
                WHERE bk_module_id IN ({placeholders})
            """
            host_count = query_one(host_count_sql)
            if host_count and host_count['count'] > 0:
                from app.utils.exceptions import APIException, CCErrorCode
                raise APIException(
                    '目标包含主机, 不允许删除',
                    error_code=CCErrorCode.CCErrTopoHasHostCheckFailed
                )

        executor.execute("""
            DELETE FROM cc_SetBase WHERE bk_set_id = :set_id AND bk_biz_id = :biz_id
        """, {'set_id': bk_inst_id, 'biz_id': bk_biz_id})
    elif bk_obj_id == 'module':
        if not bk_biz_id:
            raise ValueError('删除模块需要 bk_biz_id')

        # 复刻原项目：检查模块是否有关联主机
        host_count = query_one("""
            SELECT COUNT(*) as count FROM cc_ModuleHostConfig WHERE bk_module_id = :module_id
        """, {'module_id': bk_inst_id})
        if host_count and host_count['count'] > 0:
            from app.utils.exceptions import APIException, CCErrorCode
            raise APIException(
                '目标包含主机, 不允许删除',
                error_code=CCErrorCode.CCErrTopoHasHostCheckFailed
            )

        executor.execute("""
            DELETE FROM cc_ModuleBase WHERE bk_module_id = :module_id AND bk_biz_id = :biz_id
        """, {'module_id': bk_inst_id, 'biz_id': bk_biz_id})
    else:
        raise ValueError(f'不支持的节点类型: {bk_obj_id}')