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
                 detail: Dict[str, Any] = None):
        self.object_id = object_id
        self.instance_id = instance_id
        self.instance_name = instance_name
        self.detail = detail or {}
        self.children: List['TopoInstanceNode'] = []
        self.count = 0  # 子节点数量统计（with_statistics时使用）

    def to_dict(self, with_statistics: bool = False) -> Dict[str, Any]:
        result = {
            'bk_obj_id': self.object_id,
            'bk_inst_id': self.instance_id,
            'bk_inst_name': self.instance_name,
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
        sql = f"""
            SELECT {id_field}, {name_field}, *
            FROM {table}
            WHERE bk_supplier_account = :supplier
              AND "default" = 0
            ORDER BY {id_field}
        """
    else:
        parent_field = MODEL_PARENT_FIELD.get(model_id, 'bk_parent_id')
        sql = f"""
            SELECT {id_field}, {name_field}, {parent_field}, bk_biz_id, *
            FROM {table}
            WHERE bk_supplier_account = :supplier
              AND bk_biz_id = :bk_biz_id
            ORDER BY {id_field}
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
    root = TopoInstanceNode(
        object_id=MAINLINE_MODEL_BIZ,
        instance_id=bk_biz_id,
        instance_name=biz_name,
        detail=biz_instance if with_detail else {}
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
        set_node = TopoInstanceNode(
            object_id=MAINLINE_MODEL_SET,
            instance_id=set_id,
            instance_name=set_name,
            detail=inst if with_detail else {}
        )
        set_node_map[set_id] = set_node
        root.children.append(set_node)

    for inst in module_instances:
        module_id = inst[MODEL_ID_FIELD[MAINLINE_MODEL_MODULE]]
        module_name = inst.get(MODEL_NAME_FIELD[MAINLINE_MODEL_MODULE], f'module_{module_id}')
        parent_id = inst.get('bk_set_id') or inst.get(MODEL_PARENT_FIELD.get(MAINLINE_MODEL_MODULE, 'bk_parent_id'))

        module_node = TopoInstanceNode(
            object_id=MAINLINE_MODEL_MODULE,
            instance_id=module_id,
            instance_name=module_name,
            detail=inst if with_detail else {}
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