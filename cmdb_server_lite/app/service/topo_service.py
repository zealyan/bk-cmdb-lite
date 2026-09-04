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
import time
from typing import Dict, List, Optional, Any
from app.db.executor import query_all, query_one
from app.db.dialect import get_column_names
from app.utils.exceptions import APIException, CCErrorCode

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


# 主线关联类型（cc_ObjAsst 标识主线拓扑的边；lite 复用 bk_asst_id 表达 kind）
MAINLINE_ASST_ID = 'bk_mainline'


def model_id_field(model_id: str) -> str:
    """模型主键字段（内置模型用业务主键，自定义模型统一 bk_inst_id）。"""
    return MODEL_ID_FIELD.get(model_id, 'bk_inst_id')


def model_name_field(model_id: str) -> str:
    """模型名称字段（自定义模型统一 bk_inst_name）。"""
    return MODEL_NAME_FIELD.get(model_id, 'bk_inst_name')


def mainline_parent_of(model_id: str,
                        supplier_account: str = DEFAULT_SUPPLIER) -> Optional[str]:
    """
    返回某模型在主线中的父模型ID（cc_ObjAsst.bk_asst_id='bk_mainline' 的 target_obj_id）。

    对齐上游 SearchMainlineAssociationTopo 的 parentMap 解析。
    """
    row = query_one(
        "SELECT target_obj_id FROM cc_ObjAsst "
        "WHERE bk_asst_id = :aid AND bk_obj_id = :oid "
        "AND bk_supplier_account = :supplier",
        {'aid': MAINLINE_ASST_ID, 'oid': model_id, 'supplier': supplier_account})
    return row['target_obj_id'] if row else None


def _load_mainline_level(model_id: str, bk_biz_id: int,
                          supplier_account: str = DEFAULT_SUPPLIER) -> List[Dict[str, Any]]:
    """
    加载主线某层级模型的全部业务实例（按 default 降序、主键升序）。

    通用实现：内置(set/module)与自定义模型统一通过 InstanceService 表名解析 +
    bk_biz_id 过滤，不再写死 set/module。各实例的 bk_parent_id 指向上一级父实例，
    由 get_mainline_instance_topo 负责逐层拼接。

    Args:
        model_id: 模型ID（set/module/自定义）
        bk_biz_id: 业务ID
        supplier_account: 供应商账号

    Returns:
        实例列表
    """
    from app.service.instance_service import InstanceService

    table = InstanceService._get_table_name(model_id)
    id_field = model_id_field(model_id)
    sql = f"""
        SELECT * FROM "{table}"
        WHERE bk_supplier_account = :sup AND bk_biz_id = :biz
        ORDER BY "default" DESC, {id_field}
    """
    return query_all(sql, {'sup': supplier_account, 'biz': bk_biz_id})


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

    def to_dict(self, with_statistics: bool = False, model_name_map: Dict[str, str] = None) -> Dict[str, Any]:
        # model_name_map: {bk_obj_id: bk_obj_name}，供前端节点图标取「模型中文首字」
        # （如 应用系统→"应"），对齐原项目 topology-tree-node.vue 的 {{ data.bk_obj_name[0] }}。
        # 此前 to_dict 漏传 bk_obj_name，导致前端 mapTopoNode 回退到 obj_id 首字母（app_sys→"A"）。
        # 懒加载路径 get_mainline_children 已携带该字段，此处补齐全量树路径，二者一致。
        result = {
            'bk_obj_id': self.object_id,
            'bk_inst_id': self.instance_id,
            'bk_inst_name': self.instance_name,
            'bk_obj_name': (model_name_map or {}).get(self.object_id, self.object_id),
            'default': self.default,  # 返回 default 字段
        }
        if with_statistics:
            result['count'] = self.count
        if self.children:
            result['child'] = [child.to_dict(with_statistics, model_name_map) for child in self.children]
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
            SELECT *
            FROM {table}
            WHERE bk_supplier_account = :supplier
              AND "default" = 0
            ORDER BY {id_field}
        """
    elif model_id == MAINLINE_MODEL_SET:
        # 集群表：按 default 降序排序（空闲机池 default=1 排最前面）
        sql = f"""
            SELECT *
            FROM {table}
            WHERE bk_supplier_account = :supplier
              AND bk_biz_id = :bk_biz_id
            ORDER BY "default" DESC, {id_field}
        """
    else:
        # 模块表：按 default 降序排序（空闲机 default=1 排最前面）
        parent_field = MODEL_PARENT_FIELD.get(model_id, 'bk_parent_id')
        sql = f"""
            SELECT *
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
        SELECT *
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

    # 沿主线模型链（biz -> ... -> module）逐层按 bk_parent_id 拼装实例树，
    # 支持任意多模型多层级（自定义主线模型自动纳入，无需改此处）。
    level_nodes: Dict[str, Dict[int, TopoInstanceNode]] = {
        MAINLINE_MODEL_BIZ: {bk_biz_id: root}
    }

    for lvl in model_levels[1:]:
        insts = _load_mainline_level(lvl, bk_biz_id, supplier_account)
        node_map: Dict[int, TopoInstanceNode] = {}
        parent_lvl = model_levels[model_levels.index(lvl) - 1]
        parent_map = level_nodes.get(parent_lvl, {})
        for inst in insts:
            iid = inst[model_id_field(lvl)]
            pid = inst.get('bk_parent_id') or 0
            node = TopoInstanceNode(
                object_id=lvl,
                instance_id=iid,
                instance_name=inst.get(model_name_field(lvl), f'{lvl}_{iid}'),
                detail=inst if with_detail else {},
                default=inst.get('default', 0))
            node_map[iid] = node
            if pid in parent_map:
                parent_map[pid].children.append(node)
            else:
                # 孤儿实例（父不存在）：挂到 root 以保证可见，不参与统计聚合
                root.children.append(node)
        level_nodes[lvl] = node_map

    if with_statistics:
        module_host_count = _count_hosts_by_module(bk_biz_id, supplier_account)
        for mid, node in level_nodes.get(MAINLINE_MODEL_MODULE, {}).items():
            node.count = module_host_count.get(mid, 0)

        # 自底向上聚合：沿已拼装好的实例树后序遍历，
        # 每节点 count = 自身主机数 + 所有子节点 count 之和。
        # 用树结构而非 level_nodes 的 ID 匹配，避免「子ID 误查父层级表」导致漏累加。
        def _aggregate(node: 'TopoInstanceNode') -> int:
            total = node.count
            for child in node.children:
                total += _aggregate(child)
            node.count = total
            return total

        _aggregate(root)

    # 空闲机池（default=1 的 set）永久排在业务节点（biz）下的首位，
    # 不受自定义主线层（appsys 等）排序影响。
    # 对齐原项目 business-set-topology/children/topology-tree.vue：
    #   data.sort(a => (a.bk_obj_id === BUILTIN_MODELS.SET && a.default === 1 ? -1 : 0))
    # 因「空闲机池」的 bk_parent_id 指向 biz，而在含自定义层的主线里 set 的父模型为
    # appsys，它会作为孤儿被挂到 root.children 末尾；此处显式置顶，保证始终位于 biz 首位。
    root.children.sort(
        key=lambda n: 0 if (n.object_id == MAINLINE_MODEL_SET and n.default == 1) else 1
    )

    return root


# ---------------------------------------------------------------------------
# 模型中文名解析（供前端节点图标取"模型中文首个字"，对齐原项目节点自带 bk_obj_name）
# 原项目前端 topology-tree-node.vue: <span>{{ data.bk_obj_name[0] }}</span>
# lite 前端懒加载路径需后端在 children 中携带 bk_obj_name，才能正确显示图标首字
# （如 集群→"集"、模块→"模"、应用系统→"应"、应用子系统→"子"），避免回落到 'N'。
# ---------------------------------------------------------------------------
_MODEL_NAME_CACHE: Dict[tuple, Dict[str, str]] = {}


def get_model_name_map(supplier_account: str = DEFAULT_SUPPLIER) -> Dict[str, str]:
    """返回 {bk_obj_id: bk_obj_name} 模型中文名映射（进程内缓存）。"""
    key = (supplier_account,)
    cached = _MODEL_NAME_CACHE.get(key)
    if cached is not None:
        return cached
    rows = query_all(
        "SELECT bk_obj_id, bk_obj_name FROM cc_ObjDes WHERE bk_supplier_account = :sup",
        {'sup': supplier_account})
    mapping = {r['bk_obj_id']: r['bk_obj_name'] for r in rows}
    _MODEL_NAME_CACHE[key] = mapping
    return mapping


# ---------------------------------------------------------------------------
# biz-topo 缓存（对齐原项目 source_controller/cacheservice/cache/biz-topo）
# 缓存业务全量拓扑树 + (obj_id,inst_id)->node 索引，避免每次请求重算 + 重序列化
# 13 万节点（如 biz3）。拓扑变更（创建/删除实例）时通过 clear_topo_cache 失效。
# ---------------------------------------------------------------------------
_TOPO_CACHE: Dict[tuple, Dict[str, Any]] = {}
_TOPO_CACHE_TTL = 60  # 秒


def _topo_cache_key(bk_biz_id: int, supplier_account: str) -> tuple:
    return (bk_biz_id, supplier_account)


def _get_cached_topo(bk_biz_id: int, supplier_account: str = DEFAULT_SUPPLIER):
    """获取（或构建并缓存）业务全量拓扑树及节点索引。

    对齐原项目 cacheservice/biz-topo：用进程内缓存避免每次请求重算 + 重序列化
    13 万节点。树始终以 with_statistics=True 构建（算好聚合 count），调用方按需取用。
    """
    key = _topo_cache_key(bk_biz_id, supplier_account)
    item = _TOPO_CACHE.get(key)
    if item and (time.time() - item['ts']) < _TOPO_CACHE_TTL:
        return item
    tree = get_mainline_instance_topo(bk_biz_id, with_detail=False,
                                      with_statistics=True, supplier_account=supplier_account)
    if tree is None:
        return None
    index: Dict[tuple, 'TopoInstanceNode'] = {}

    def _walk(n):
        index[(n.object_id, n.instance_id)] = n
        for c in n.children:
            _walk(c)

    _walk(tree)
    item = {'tree': tree, 'index': index, 'ts': time.time()}
    _TOPO_CACHE[key] = item
    return item


def clear_topo_cache(bk_biz_id: int = None, supplier_account: str = DEFAULT_SUPPLIER):
    """失效 biz-topo 缓存。拓扑变更（创建/删除实例）时调用。"""
    if bk_biz_id is None:
        _TOPO_CACHE.clear()
    else:
        _TOPO_CACHE.pop(_topo_cache_key(bk_biz_id, supplier_account), None)


def get_mainline_children(bk_biz_id: int, parent_obj_id: str, parent_inst_id: int,
                          with_statistics: bool = True,
                          supplier_account: str = DEFAULT_SUPPLIER) -> Optional[List[Dict[str, Any]]]:
    """获取主线实例某父节点的【直接子层】，用于前端分层懒加载。

    对齐原项目前端 business-topology 的 lazy-method 分层加载思想：不再一次性
    返回整棵 13 万节点树（34MB 响应），而是按父节点逐层懒加载，每层仅几百 KB。

    复用 biz-topo 缓存的全量树 O(1) 定位父节点，返回其 children 一层（精简字段）。

    Args:
        bk_biz_id: 业务ID
        parent_obj_id: 父节点模型ID（biz/set/module/sys/subsys...）
        parent_inst_id: 父节点实例ID
        with_statistics: 是否返回聚合主机数 count
        supplier_account: 供应商账号
    Returns:
        [ {bk_obj_id, bk_inst_id, bk_inst_name, default, count, is_leaf}, ... ]
        None 表示业务不存在；空列表表示父节点无子层或不存在。
    """
    item = _get_cached_topo(bk_biz_id, supplier_account)
    if item is None:
        return None
    parent = item['index'].get((parent_obj_id, parent_inst_id))
    if parent is None:
        return []

    # 主线链末端（module 总是主线最后一层），其下是 host 而非主线实例 -> 叶子
    model_levels = get_mainline_model_top(supplier_account).leftest_object_id_list()
    last_obj = model_levels[-1] if model_levels else MAINLINE_MODEL_MODULE

    # 模型中文名映射：供前端节点图标取"模型中文首个字"（集群→"集"、模块→"模"…）
    model_name_map = get_model_name_map(supplier_account)

    children = []
    for ch in parent.children:
        obj_id = ch.object_id
        children.append({
            'bk_obj_id': obj_id,
            'bk_inst_id': ch.instance_id,
            'bk_inst_name': ch.instance_name,
            'bk_obj_name': model_name_map.get(obj_id, obj_id),
            # 节点必须携带 bk_biz_id：前端 host-list 依据它查询主机列表
            # （biz 节点用 bk_inst_id，其余节点用 bk_biz_id），缺省会返回空列表。
            'bk_biz_id': bk_biz_id,
            'default': ch.default,
            'count': ch.count if with_statistics else 0,
            'is_leaf': obj_id == last_obj,
            # 空闲机池：default=1 的集群（set），始终置业务(biz)下首位、隐藏"新建"按钮
            'is_idle_set': obj_id == MAINLINE_MODEL_SET and ch.default == 1,
        })
    return children


def get_topo_node_statistics(bk_biz_id: int, condition: List[Dict[str, Any]],
                             supplier_account: str = DEFAULT_SUPPLIER) -> List[Dict[str, Any]]:
    """批量获取拓扑节点主机数统计（对齐原项目 GetTopoNodeHostAndSerInstCount）。

    复用 biz-topo 缓存树（_get_cached_topo）：构建时已按 with_statistics=True 为每个节点
    聚合 count（module 主机数 + 自底向上后序累加），此处按 (obj_id, inst_id) O(1) 定位直接
    返回，避免对 condition 逐节点递归查库（原实现对 1000 节点需 ~20s，缓存命中为毫秒级）。
    语义与前端树节点展示的 count 完全一致（同一缓存源）。

    Args:
        bk_biz_id: 业务ID
        condition: [{bk_obj_id, bk_inst_id}, ...]
        supplier_account: 供应商账号

    Returns:
        [{bk_obj_id, bk_inst_id, host_count, service_instance_count}, ...]
    """
    item = _get_cached_topo(bk_biz_id, supplier_account)
    index = item['index'] if item else {}
    results: List[Dict[str, Any]] = []
    for cond in condition:
        obj_id = cond.get('bk_obj_id')
        inst_id = cond.get('bk_inst_id')
        if not obj_id or inst_id is None:
            continue
        try:
            inst_id = int(inst_id)
        except (TypeError, ValueError):
            continue
        node = index.get((obj_id, inst_id))
        results.append({
            'bk_obj_id': obj_id,
            'bk_inst_id': inst_id,
            'host_count': node.count if node else 0,
            'service_instance_count': 0,
        })
    return results


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


def get_mainline_node_host_count(bk_obj_id: str, bk_inst_id: int,
                                 bk_biz_id: int = None,
                                 supplier_account: str = DEFAULT_SUPPLIER) -> int:
    """
    通用主线节点主机数统计：支持 biz/set/module 与任意自定义主线层（如 appsys）。

    自定义主线层（appsys、zone 等）与 host 无直接字段关联，需沿 bk_parent_id 递归
    收集其下所有 module 实例，再聚合 cc_ModuleHostConfig 计数。依赖主线模型顺序
    （cc_ObjAsst.bk_mainline），天然支持任意多层级 biz→appsys→zone→set→module。

    Args:
        bk_obj_id: 节点模型ID（biz/set/module/自定义主线层）
        bk_inst_id: 节点实例ID
        bk_biz_id: 业务ID（自定义层与 set 必须）
        supplier_account: 供应商账号

    Returns:
        该节点范围下的主机总数
    """
    if bk_obj_id == 'biz':
        return get_biz_host_count(bk_inst_id, supplier_account)
    if bk_obj_id == 'set':
        if not bk_biz_id:
            return 0
        return get_set_host_count(bk_inst_id, bk_biz_id, supplier_account)
    if bk_obj_id == 'module':
        return get_module_host_count(bk_inst_id, supplier_account)

    # 自定义主线层：需 bk_biz_id 以沿主线递归统计其下主机
    if bk_biz_id is None:
        return 0
    mod_ids = _collect_descendant_module_ids(bk_obj_id, [bk_inst_id],
                                             bk_biz_id, supplier_account)
    if not mod_ids:
        return 0
    placeholders = ', '.join([f':mid_{i}' for i in range(len(mod_ids))])
    params = {'sup': supplier_account}
    for i, m in enumerate(mod_ids):
        params[f'mid_{i}'] = m
    sql = (f'SELECT COUNT(DISTINCT bk_host_id) AS cnt FROM cc_ModuleHostConfig '
           f'WHERE bk_supplier_account = :sup AND bk_module_id IN ({placeholders})')
    row = query_one(sql, params)
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


# 缓存 cc_HostBase 表真实列名（get_column_names 跨库内省获取，支持自定义属性）
_HOST_BASE_COLUMNS = None

def _get_host_base_columns():
    global _HOST_BASE_COLUMNS
    if _HOST_BASE_COLUMNS is None:
        try:
            _HOST_BASE_COLUMNS = set(get_column_names('cc_HostBase'))
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
    custom_module_ids = []  # 自定义主线层（appsys 等）递归收集到的 module 实例 id

    for cond in conditions:
        obj_id = cond.get('bk_obj_id', '')
        cond_items = cond.get('condition', [])

        if obj_id == 'host':
            host_cond_items.extend(cond_items)
        elif obj_id == 'set':
            set_cond_items.extend(cond_items)
        elif obj_id == 'module':
            module_cond_items.extend(cond_items)
        else:
            # 自定义主线层（appsys 等）：解析实例 id，递归收集其下所有 module 实例 id，
            # 后续与 module 条件合并为 bk_module_id IN (...)，实现「选中任意主线节点查主机」。
            inst_ids = _parse_instance_ids_from_cond(cond, obj_id)
            if inst_ids:
                mids = _collect_descendant_module_ids(
                    obj_id, inst_ids, bk_biz_id, supplier_account)
                custom_module_ids.extend(mids)

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

    # module 条件过滤：先查 cc_ModuleBase 获取符合的 bk_module_id，
    # 并与自定义主线层递归收集到的 module id 取并集。
    if module_cond_items:
        module_ids = _filter_topo_ids('module', module_cond_items, bk_biz_id, supplier_account)
        if module_ids is None:
            module_ids = []
        if custom_module_ids:
            module_ids = list(set(module_ids) | set(custom_module_ids))
        if not module_ids:
            return {'info': [], 'count': 0}
        placeholders = ', '.join([f":mid_{i}" for i in range(len(module_ids))])
        topo_where.append(f'bk_module_id IN ({placeholders})')
        for i, mid in enumerate(module_ids):
            topo_params[f'mid_{i}'] = mid
    elif custom_module_ids:
        module_ids = list(set(custom_module_ids))
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
    #   2. 字段必须是 cc_HostBase 真实存在的列（get_column_names 跨库内省获取，支持自定义属性）
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


def _parse_instance_ids_from_cond(cond: Dict[str, Any], obj_id: str) -> List[int]:
    """
    从自定义主线层条件中解析目标实例ID列表。
    支持 {field: '<model_id_field>'|'bk_inst_id', operator: '$eq'|'$in', value: ...}。
    例: appsys 节点 → field='bk_inst_id', operator='$eq', value=11472
    """
    id_field = model_id_field(obj_id)
    cond_items = cond.get('condition', [])
    ids: List[int] = []
    for item in cond_items:
        field = item.get('field')
        if field not in (id_field, 'bk_inst_id'):
            continue
        operator = item.get('operator', '$eq')
        value = item.get('value')
        if operator == '$eq':
            try:
                ids.append(int(value))
            except (TypeError, ValueError):
                pass
        elif operator == '$in' and isinstance(value, list):
            for v in value:
                try:
                    ids.append(int(v))
                except (TypeError, ValueError):
                    pass
    return ids


def _collect_descendant_module_ids(root_obj_id: str, root_inst_ids: List[int],
                                    bk_biz_id: int,
                                    supplier_account: str = DEFAULT_SUPPLIER) -> List[int]:
    """
    从某主线实例出发，沿 bk_parent_id 逐层向下递归收集其下所有 module 实例ID。

    用于支持「选中 appsys 等自定义主线节点查其下所有主机」：
    业务拓扑选中任意节点时，其下所有主机 = 该节点子树内所有 module 的主机。
    通用处理任意多层级（appsys→set→module / biz→appsys→zone→set→module 等），
    依赖主线模型顺序（cc_ObjAsst.bk_mainline 解析的 leftest_object_id_list）。

    Args:
        root_obj_id: 根模型ID（如 'appsys'）
        root_inst_ids: 根实例ID列表
        bk_biz_id: 业务ID
        supplier_account: 供应商账号

    Returns:
        module 实例ID列表（root 已是 module 层时返回自身）
    """
    from app.service.instance_service import InstanceService

    if not root_inst_ids:
        return []

    levels = get_mainline_model_top(supplier_account).leftest_object_id_list()
    if root_obj_id not in levels:
        return []
    start_idx = levels.index(root_obj_id)

    # root 已是 module 层：直接返回自身
    if levels[start_idx] == MAINLINE_MODEL_MODULE:
        return list(root_inst_ids)

    current_ids = list(root_inst_ids)
    module_ids: List[int] = []
    for lvl in levels[start_idx + 1:]:
        if not current_ids:
            break
        table = InstanceService._get_table_name(lvl)
        id_field = model_id_field(lvl)
        placeholders = ', '.join([f":pid_{i}" for i in range(len(current_ids))])
        params = {'sup': supplier_account, 'biz': bk_biz_id}
        for i, pid in enumerate(current_ids):
            params[f'pid_{i}'] = pid
        sql = (f'SELECT "{id_field}" AS iid FROM "{table}" '
               f'WHERE bk_supplier_account = :sup AND bk_biz_id = :biz '
               f'AND bk_parent_id IN ({placeholders})')
        rows = query_all(sql, params)
        current_ids = [r['iid'] for r in rows]
        if lvl == MAINLINE_MODEL_MODULE:
            module_ids = current_ids
            break
    return module_ids


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


def _mainline_instance_exists(model_id: str, inst_id: int,
                              supplier_account: str = DEFAULT_SUPPLIER) -> bool:
    """主线某模型下是否真实存在该实例（用于路径上溯的父模型归属判定）。"""
    from app.service.instance_service import InstanceService
    tbl = InstanceService._get_table_name(model_id)
    idf = InstanceService._get_id_field(model_id)
    row = query_one(
        f'SELECT 1 FROM "{tbl}" '
        f'WHERE "{idf}" = :i AND bk_supplier_account = :sup',
        {'i': int(inst_id), 'sup': supplier_account})
    return bool(row)


def _resolve_mainline_parent_model(cur_obj: str, pid: int,
                                   supplier_account: str = DEFAULT_SUPPLIER) -> Optional[str]:
    """返回 bk_parent_id=pid 实际归属的主线模型。

    主线数据允许「跳级挂载」（如空闲机池 set 直接 bk_parent_id=biz、
    或历史数据 set 跳过 subsys），不能只按模型链取一级父模型，否则路径
    上溯会在中间层断掉。此处沿模型链（父→祖父→…→biz）逐级尝试，
    返回第一个真正持有该实例 ID 的祖先模型。
    """
    m = mainline_parent_of(cur_obj, supplier_account)
    while m:
        if _mainline_instance_exists(m, pid, supplier_account):
            return m
        m = mainline_parent_of(m, supplier_account)
    return None


def get_instance_mainline_path(obj_id: str, inst_id: int,
                                bk_biz_id: int = None,
                                supplier_account: str = DEFAULT_SUPPLIER) -> List[Dict[str, Any]]:
    """
    从某主线实例沿 bk_parent_id 逐级上溯到业务(biz)，返回完整主线路径（含自定义层）。

    用于：主机所属拓扑、节点面包屑、转移对话框懒加载树恢复默认选中等
    需要"按主线顺序还原完整层级链"的场景。
    例如 biz->appsys->set->module 下，module 实例返回
    [{biz}, {appsys}, {set}, {module}]，自动纳入任意自定义主线层，不写死层级。

    支持跳级挂载：若某节点 bk_parent_id 直接指向更高层祖先（如 set 直接挂 biz），
    父模型归属由 _resolve_mainline_parent_model 沿模型链向上解析，路径不中断。

    Args:
        obj_id: 起始模型ID（通常为 module，也可为 set / 任意主线层）
        inst_id: 起始实例ID
        bk_biz_id: 业务ID（仅用于调试断言，上溯完全由 bk_parent_id 驱动，可不传）
        supplier_account: 供应商账号

    Returns:
        从 biz 到当前实例的主线节点链（顺序 biz ... leaf），每节点
        { bk_obj_id, bk_inst_id, bk_inst_name }
    """
    from app.service.instance_service import InstanceService
    chain = []
    cur_obj, cur_inst = obj_id, int(inst_id)
    guard = 0
    while cur_obj and guard < 32:
        tbl = InstanceService._get_table_name(cur_obj)
        idf = InstanceService._get_id_field(cur_obj)
        namef = model_name_field(cur_obj)
        # biz 是主线根，实例表（cc_ApplicationBase）无 bk_parent_id 列，单独处理
        parent_col = '' if cur_obj == MAINLINE_MODEL_BIZ else ', bk_parent_id'
        row = query_one(
            f'SELECT "{idf}", "{namef}"{parent_col}, bk_biz_id '
            f'FROM "{tbl}" '
            f'WHERE "{idf}" = :i AND bk_supplier_account = :sup',
            {'i': cur_inst, 'sup': supplier_account})
        if not row:
            break
        chain.append({
            'bk_obj_id': cur_obj,
            'bk_inst_id': int(row[idf]),
            'bk_inst_name': row[namef] if row[namef] is not None else f'{cur_obj}_{cur_inst}'
        })
        if cur_obj == MAINLINE_MODEL_BIZ:
            break
        nxt = row.get('bk_parent_id')
        if nxt is None:
            break
        pmodel = _resolve_mainline_parent_model(cur_obj, int(nxt), supplier_account)
        if not pmodel:
            break
        cur_obj, cur_inst = pmodel, int(nxt)
        guard += 1
    chain.reverse()
    return chain


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
            'bk_module_name': row['bk_module_name'],
            # 通用主线路径：沿 bk_parent_id 上溯到 biz，含 appsys 等自定义层。
            # 前端"所属拓扑"据此拼完整层级链（biz / appsys / set / module ...）。
            'topo_path': get_instance_mainline_path(
                MAINLINE_MODEL_MODULE, module_id, biz_id, supplier_account)
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

    委托 create_mainline_instance：集群是业务(biz)主线下的子模型，
    bk_parent_id = 业务ID，bk_biz_id 继承业务。

    Args:
        bk_biz_id: 业务ID
        names: 集群名称列表
        supplier_account: 供应商账号

    Returns:
        { 'created': [...], 'error_names': [...] }
    """
    # 验证业务是否存在
    biz = query_one("""
        SELECT bk_biz_id FROM cc_ApplicationBase
        WHERE bk_biz_id = :biz_id AND bk_supplier_account = :supplier
    """, {'biz_id': bk_biz_id, 'supplier': supplier_account})
    if not biz:
        raise ValueError(f'业务 {bk_biz_id} 不存在')

    return create_mainline_instance(
        parent_obj_id=MAINLINE_MODEL_BIZ,
        parent_inst_id=bk_biz_id,
        model_id=MAINLINE_MODEL_SET,
        names=names,
        bk_biz_id=bk_biz_id,
        supplier_account=supplier_account)


def create_module(bk_set_id: int, names: List[str],
                  bk_biz_id: int = None, supplier_account: str = DEFAULT_SUPPLIER,
                  attrs: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    创建模块（批量）

    委托 create_mainline_instance：模块的父模型来自主线（标准链为 set；
    若 CLI 在 set 与 module 间插入了自定义模型，则父为那个自定义模型）。
    parent_inst_id 即父实例ID（标准链即 bk_set_id；自定义链为自定义实例ID）。

    Args:
        bk_set_id: 父实例ID（标准链为集群ID，自定义链为自定义层级实例ID）
        names: 模块名称列表
        bk_biz_id: 业务ID（可选，不传则从父实例继承）
        supplier_account: 供应商账号
        attrs: 模块额外属性（如 service_category_id / bk_module_type），对齐上游 CreateModule

    Returns:
        { 'created': [...], 'error_names': [...] }
    """
    parent_obj_id = mainline_parent_of(MAINLINE_MODEL_MODULE, supplier_account) \
        or MAINLINE_MODEL_SET
    return create_mainline_instance(
        parent_obj_id=parent_obj_id,
        parent_inst_id=bk_set_id,
        model_id=MAINLINE_MODEL_MODULE,
        names=names,
        bk_biz_id=bk_biz_id,
        supplier_account=supplier_account,
        attrs=attrs)


def ensure_idle_pool(bk_biz_id: int,
                     supplier_account: str = DEFAULT_SUPPLIER) -> Optional[int]:
    """
    确保业务下存在「空闲机池」（default=1 的 set）+ 内部模块（空闲机/故障机/待回收）。

    对齐原项目 CreateBusiness：业务创建时自动生成空闲机池，保证业务拓扑树
    首位恒为空闲机池（读取层按 `ORDER BY "default" DESC` 排序，default=1 排第一）。
    该函数幂等：若业务下已存在 default=1 的 set 则直接返回，不重复创建。

    结构（与 migrate 初始化一致）：
        - 空闲机池 set：default=1，bk_parent_id=biz
        - 空闲机 module：default=1
        - 故障机 module：default=2
        - 待回收 module：default=3

    Args:
        bk_biz_id: 业务ID
        supplier_account: 供应商账号
    Returns:
        空闲机池 set_id；若创建失败返回 None
    """
    from app.db.executor import SQLExecutor

    existing = query_one(
        'SELECT bk_set_id FROM cc_SetBase '
        'WHERE bk_biz_id=:b AND bk_supplier_account=:s AND "default"=1',
        {'b': bk_biz_id, 's': supplier_account})
    if existing:
        return existing['bk_set_id']

    # 1) 空闲机池集群（default=1），直接挂在业务(biz)下
    sres = create_mainline_instance('biz', bk_biz_id, 'set', ['空闲机池'],
                                    supplier_account=supplier_account)
    if not sres.get('created'):
        return None
    set_id = sres['created'][0]['bk_set_id']

    executor = SQLExecutor()
    executor.execute(
        'UPDATE cc_SetBase SET "default" = :d '
        'WHERE bk_set_id = :sid AND bk_supplier_account = :s',
        {'d': 1, 'sid': set_id, 's': supplier_account})

    # 2) 内部模块：空闲机 / 故障机 / 待回收（default=1/2/3）
    mres = create_mainline_instance('set', set_id, 'module',
                                   ['空闲机', '故障机', '待回收'],
                                   bk_biz_id=bk_biz_id,
                                   supplier_account=supplier_account)
    mids = [m['bk_module_id'] for m in mres.get('created', [])]
    module_defaults = {0: 1, 1: 2, 2: 3}  # 按创建顺序映射默认标识
    for idx, mid in enumerate(mids):
        dv = module_defaults.get(idx)
        if dv is None:
            break
        executor.execute(
            'UPDATE cc_ModuleBase SET "default" = :d '
            'WHERE bk_module_id = :mid AND bk_supplier_account = :s',
            {'d': dv, 'mid': mid, 's': supplier_account})
    return set_id


def create_biz(bk_biz_name: str,
               supplier_account: str = DEFAULT_SUPPLIER,
               **extra) -> Dict[str, Any]:
    """
    创建业务（CreateBusiness）

    业务是主线拓扑的根节点，无父节点（bk_parent_id），写入内置表 cc_ApplicationBase。
    主键 bk_biz_id 由全局序列 generate_id 自动发号；bk_biz_name 全局唯一（单键约束，
    重名时由 InstanceService.create_instance 的 check_unique 兜底（并发插入场景），
    主路径已在 create_biz 内做前置唯一性校验并返回语义正确的 1199014。

    对齐上游 CreateBusiness：业务名称必填、供应商隔离（bk_supplier_account 维度）。

    Args:
        bk_biz_name: 业务名称（必填，全局唯一）
        supplier_account: 供应商账号，默认 '0'
        extra: 其它可选业务属性（bk_biz_maintainer / bk_biz_developer / bk_biz_productor 等），
                透传给 create_instance，由其 valid_fields 收敛到真实表列

    Returns:
        创建后的业务实例字典 { bk_biz_id, bk_biz_name, default, bk_supplier_account, ... }
    """
    from app.service.instance_service import InstanceService

    name = (bk_biz_name or '').strip()
    if not name:
        raise APIException('业务名称不能为空',
                           error_code=CCErrorCode.CCErrCommParamsInvalid)

    # 业务根节点（无父），系统字段占位；可选业务属性经 valid_fields 过滤后落库
    data = {
        'bk_biz_name': name,
        'default': 0,
        'bk_supplier_account': supplier_account,
        'creator': 'admin',
        'modifier': 'admin',
    }
    reserved = ('bk_biz_id', 'bk_biz_name', 'default', 'bk_parent_id',
                'bk_inst_id', 'bk_obj_id', 'id', '_id', 'create_time',
                'last_time', 'creator', 'modifier', 'bk_supplier_account')
    for k, v in (extra or {}).items():
        if k in reserved or v is None:
            continue
        data[k] = v

    try:
        inst = InstanceService.create_instance('biz', data)
    except APIException as e:
        # create_instance 内部 check_unique 在重名时抛异常（文案含「已存在」）。
        # 将其归一为语义正确的重复错误码 1199014，与 create_mainline_instance 的
        # 批量创建一致；其余内部异常原样上抛（由全局处理器统一呈现）。
        if '已存在' in str(e):
            raise APIException(str(e),
                               error_code=CCErrorCode.CCErrCommDuplicateItem)
        raise
    except Exception as e:
        raise APIException(f'创建业务失败: {str(e)}',
                           error_code=CCErrorCode.CCErrTopoInstCreateFailed)

    # 对齐原项目 CreateBusiness：业务创建时自动初始化空闲机池（default=1 集群 + 内部模块），
    # 保证业务拓扑树首位恒为空闲机池（读取层按 `ORDER BY "default" DESC` 排序）。
    # 与业务根节点创建解耦：空闲机池初始化失败不影响业务创建主流程，仅告警，可后续补建。
    try:
        ensure_idle_pool(inst['bk_biz_id'], supplier_account)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f'业务 {inst.get("bk_biz_id")} 已创建，但空闲机池初始化失败: {e}')

    return dict(inst)


def _resolve_set_ancestor(parent_obj_id: str, parent_inst_id: int,
                          supplier_account: str = DEFAULT_SUPPLIER) -> int:
    """
    解析 module 所属 set 实例 ID（module 的 bk_set_id 为 NOT NULL 必填列）。

    对齐上游：module 在主线拓扑中始终位于 set 之下，无论中间是否插入了自定义层级
    （如 biz->rack->set->zone->module），其 bk_set_id 都指向主线上的 set 祖先实例。
    做法：从直接父实例沿 bk_parent_id 逐级上溯，同时沿主线父链确认模型，直到命中 set。
    """
    from app.service.instance_service import InstanceService
    cur_model = parent_obj_id
    cur_inst = int(parent_inst_id)
    guard = 0
    while cur_model != MAINLINE_MODEL_SET and guard < 32:
        pmodel = mainline_parent_of(cur_model, supplier_account)
        if not pmodel:
            return 0
        tbl = InstanceService._get_table_name(cur_model)
        idf = InstanceService._get_id_field(cur_model)
        row = query_one(
            f'SELECT bk_parent_id FROM "{tbl}" '
            f'WHERE "{idf}" = :i AND bk_supplier_account = :sup',
            {'i': cur_inst, 'sup': supplier_account})
        if not row or row.get('bk_parent_id') is None:
            return 0
        cur_model = pmodel
        cur_inst = int(row['bk_parent_id'])
        guard += 1
    return cur_inst if cur_model == MAINLINE_MODEL_SET else 0


def resolve_module_service_category(bk_biz_id: int,
                                    supplier_account: str,
                                    raw_sc_id) -> int:
    """解析并校验模块的服务分类ID（对齐上游 CreateModule.checkServiceTemplateParam）。

    上游语义（scene_server/topo_server/logics/inst/module.go）：
      - 未传（0/None）：回退到内置默认分类（bk_biz_id=0 且 is_built_in=1）；
        上游在无默认分类时报 CCErrProcGetDefaultServiceCategoryFailed，lite 宽容落 0 以兼容
        空闲机池等内部模块（不要求必须选分类）。
      - 已传（>0）：必须存在于 cc_ServiceCategory 且同租户；
        业务隔离：分类 bk_biz_id==0（全局内置/系统内置）允许任意业务使用；
        否则必须等于模块所属业务 bk_biz_id，否则视为非法（CCErrCommParamsInvalid）。

    Args:
        bk_biz_id: 模块所属业务ID
        supplier_account: 供应商账号
        raw_sc_id: 前端传入的 service_category_id（可能为空串 / 'default' / int）
    Returns:
        校验通过后的 service_category_id（int）
    """
    try:
        sc_id = int(raw_sc_id) if raw_sc_id not in (None, '', 'default') else 0
    except (TypeError, ValueError):
        sc_id = 0

    if sc_id <= 0:
        # 回退到内置默认分类（两级内置 Default 的【二级】分类 id，
        # 对齐上游 addDefaultCategory 返回值 / GetDefaultServiceCategory）。
        # 未初始化（无内置分类）时宽容落 0，不阻塞空闲机池等内部模块创建。
        from app.service.service_category_service import get_default_category_id
        default_id = get_default_category_id(supplier_account)
        return int(default_id) if default_id else 0

    cat = query_one(
        "SELECT id, bk_biz_id FROM cc_ServiceCategory "
        "WHERE id = :cid AND bk_supplier_account = :s",
        {'cid': sc_id, 's': supplier_account})
    if not cat:
        raise APIException(
            f'服务分类不存在: service_category_id={sc_id}',
            error_code=CCErrorCode.CCErrCommParamsInvalid)
    cat_biz = int(cat['bk_biz_id'])
    # 业务隔离：全局内置(bk_biz_id=0)任意业务可用；否则须与本模块业务一致
    if cat_biz != 0 and cat_biz != int(bk_biz_id or 0):
        raise APIException(
            '服务分类不属于当前业务',
            error_code=CCErrorCode.CCErrCommParamsInvalid)
    return sc_id


def create_mainline_instance(parent_obj_id: str, parent_inst_id: int,
                             model_id: str, names: List[str],
                             bk_biz_id: int = None,
                             supplier_account: str = DEFAULT_SUPPLIER,
                             attrs: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    在主线某父实例下创建子模型实例（支持任意层级，对齐上游 SetMainlineInstAssociation）。

    语义：
    - 子实例 bk_parent_id = 父实例ID（主线父实例指针，每个主线实例表均含该列）
    - 子实例 bk_biz_id 继承自父实例（主线实例按业务归属）
    - 内置模型 set：父为 biz，bk_parent_id=业务ID
    - 内置模型 module：父为 set（或自定义层级），额外回填 bk_set_id 以兼容 set/module 专用接口
    - 自定义模型：bk_parent_id + bk_biz_id 通用两列承载

    复用 InstanceService.create_instance（统一校验 / 唯一约束 / 类型转换），
    仅通过 data 透传 bk_parent_id / bk_biz_id（已加入 SYSTEM_FIELDS）。

    Args:
        parent_obj_id: 父模型ID（biz/set/module/自定义）
        parent_inst_id: 父实例ID
        model_id: 待创建的子模型ID
        names: 实例名称列表
        bk_biz_id: 业务ID（parent=biz 时即 parent_inst_id；其余从父实例继承，可缺省）
        supplier_account: 供应商账号

    Returns:
        { 'created': [...], 'error_names': [...] }
    """
    from app.service.instance_service import InstanceService

    # 解析业务归属：父为 biz 时直接等于父实例ID；否则取父实例的 bk_biz_id
    if parent_obj_id == MAINLINE_MODEL_BIZ:
        resolved_biz = int(parent_inst_id)
    elif bk_biz_id is not None:
        resolved_biz = int(bk_biz_id)
    else:
        parent_table = InstanceService._get_table_name(parent_obj_id)
        parent_id_field = InstanceService._get_id_field(parent_obj_id)
        prow = query_one(
            f'SELECT bk_biz_id FROM "{parent_table}" '
            f'WHERE "{parent_id_field}" = :pid AND bk_supplier_account = :sup',
            {'pid': parent_inst_id, 'sup': supplier_account})
        resolved_biz = int(prow['bk_biz_id']) if prow and prow.get('bk_biz_id') else 0

    # 过滤空名称与去重
    unique_names = []
    for name in names:
        name = (name or '').strip()
        if name and name not in unique_names:
            unique_names.append(name)

    created = []
    error_names = []

    # 名称列：自定义模型用 bk_inst_name，内置模型用专属列
    # （bk_set_name/bk_module_name/bk_biz_name）。create_instance 按真实表列收敛数据，
    # 若恒用 bk_inst_name 写内置模型会被过滤掉，导致名称空值触发 NOT NULL。
    name_field = model_name_field(model_id)

    for name in unique_names:
        data = {
            name_field: name,
            'bk_parent_id': int(parent_inst_id),
            'bk_biz_id': resolved_biz,
            'default': 0,
            'creator': 'admin',
            'modifier': 'admin',
        }
        # 自定义层额外属性（如 appsys/zone 的业务字段）：合并到实例 data，
        # 但保留系统/拓扑列（bk_parent_id/bk_biz_id/name/default/creator/modifier）
        # 不被覆盖，由 InstanceService.create_instance 的 valid_fields 进一步收敛。
        if attrs:
            for k, v in attrs.items():
                if k in ('bk_parent_id', 'bk_biz_id', name_field,
                         'default', 'creator', 'modifier', 'id',
                         'bk_inst_id', 'bk_obj_id', 'create_time', 'last_time',
                         'bk_supplier_account'):
                    continue
                data[k] = v
        # 模块额外回填 bk_set_id（NOT NULL）：沿主线父链上溯定位 set 祖先实例，
        # 兼容「set 与 module 间插入自定义层级」的情况（如 biz->rack->set->zone->module）。
        if model_id == MAINLINE_MODEL_MODULE:
            data['bk_set_id'] = _resolve_set_ancestor(
                parent_obj_id, parent_inst_id, supplier_account)
            # 服务分类（对齐上游 CreateModule）：校验存在性 + 业务隔离，
            # 未传则回退内置默认分类。最终落库到 cc_ModuleBase.service_category_id。
            raw_sc = (attrs or {}).get('service_category_id')
            data['service_category_id'] = resolve_module_service_category(
                resolved_biz, supplier_account, raw_sc)
            # 模块类型（对齐上游 bk_module_type / DefaultModuleType="1"）：
            # 缺省兜底为「普通」(1)，允许通过 attrs 显式指定（如 2=数据库）。
            data['bk_module_type'] = str((attrs or {}).get('bk_module_type') or '1')
        try:
            inst = InstanceService.create_instance(model_id, data)
            inst_id = inst.get(model_id_field(model_id)) or inst.get('bk_inst_id')
            created.append({
                # 同时返回模型专属主键字段名（bk_set_id/bk_module_id/...）与通用
                # bk_inst_id，兼容前端按具体模型字段取值（对齐上游返回结构）。
                model_id_field(model_id): inst_id,
                'bk_inst_id': inst_id,
                'bk_inst_name': inst.get(name_field) or inst.get('bk_inst_name'),
                'bk_obj_id': model_id,
                'bk_parent_id': int(parent_inst_id),
                'bk_biz_id': resolved_biz,
            })
        except Exception as e:
            error_names.append({'name': name, 'error': str(e)})

    return {'created': created, 'error_names': error_names}


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
                   service_category_id, bk_module_type, "default", bk_supplier_account,
                   create_time, last_time, creator, modifier
            FROM cc_ModuleBase
            WHERE bk_module_id = :module_id AND bk_biz_id = :biz_id AND bk_supplier_account = :supplier
        """, {'module_id': bk_inst_id, 'biz_id': bk_biz_id, 'supplier': supplier_account})
    else:
        # 自定义业务拓扑模型（自定义主线层，如 appsys）：经通用实例表读取。
        # 对齐上游通用 FindInst：任意主线模型实例统一按 ObjectBase 分表读取，
        # 与 delete_node 的自定义层分支保持一致。
        from app.service.instance_service import InstanceService
        model_tree = get_mainline_model_top(supplier_account)
        levels = model_tree.leftest_object_id_list()
        if bk_obj_id not in levels:
            raise ValueError(f'不支持的节点类型: {bk_obj_id}')
        result = InstanceService.get_instance(bk_obj_id, bk_inst_id)
        if not result:
            raise ValueError(f'{bk_obj_id} 节点 {bk_inst_id} 不存在')

    if not result:
        raise ValueError(f'{bk_obj_id} 节点 {bk_inst_id} 不存在')

    return dict(result)


def update_node(bk_obj_id: str, bk_inst_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新节点信息（biz/set/module 及自定义主线层）

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
        # 自定义业务拓扑模型（自定义主线层，如 appsys）：经通用实例表更新。
        # 对齐上游通用 UpdateInst：任意主线模型实例统一按 ObjectBase 分表更新，
        # 由 InstanceService.update_instance 复用字段校验 / 唯一性校验 / last_time 刷新。
        from app.service.instance_service import InstanceService
        # 主线模型为全局定义（supplier='0'），校验 obj_id 是否为主线链成员即可
        model_tree = get_mainline_model_top()
        levels = model_tree.leftest_object_id_list()
        if bk_obj_id not in levels:
            raise ValueError(f'不支持的节点类型: {bk_obj_id}')
        InstanceService.update_instance(bk_obj_id, bk_inst_id, params)

    return {'bk_inst_id': bk_inst_id}


def _check_inst_associated(obj_id: str, inst_id: int) -> bool:
    """检查实例是否被其它实例关联引用（作为目标）。

    对齐上游 deleteInsts 内 asst.CheckAssociations：被其它实例关联引用的实例不允许删除。
    """
    from app.service.association_service import get_inst_asst_table_name
    table = get_inst_asst_table_name(obj_id)
    row = query_one(
        f'SELECT COUNT(*) as count FROM "{table}" '
        f'WHERE bk_asst_inst_id = :inst_id AND bk_asst_obj_id = :obj_id',
        {'inst_id': inst_id, 'obj_id': obj_id})
    return bool(row and row['count'] > 0)


def _clean_instance_associations(bk_obj_id: str, bk_inst_id: int, executor) -> None:
    """删除实例前清理实例关联分表，对齐 InstanceService.delete_instances：

    1) 删除自身分表（cc_InstAsst_0_pub_{obj}）中作为源与作为目标的记录；
    2) 扫描对端模型分表，清理其中指向本实例的冗余记录。

    避免删除 set/module 后在 cc_InstAsst_* 中遗留悬挂关联（孤儿数据）。
    """
    from app.service.association_service import get_inst_asst_table_name

    own_table = get_inst_asst_table_name(bk_obj_id)
    params = {'model_id': bk_obj_id, 'inst_id': bk_inst_id}

    # 先查出涉及的对端模型（用于清理对端分表冗余记录）
    try:
        related_dest = query_all(
            f'SELECT DISTINCT bk_asst_obj_id FROM "{own_table}" '
            f'WHERE bk_obj_id = :model_id AND bk_inst_id = :inst_id',
            params) or []
        related_src = query_all(
            f'SELECT DISTINCT bk_obj_id FROM "{own_table}" '
            f'WHERE bk_asst_obj_id = :model_id AND bk_asst_inst_id = :inst_id',
            params) or []
    except Exception:
        related_dest = []
        related_src = []

    # 删除自身分表（源 + 目标）
    executor.execute(
        f'DELETE FROM "{own_table}" '
        f'WHERE bk_obj_id = :model_id AND bk_inst_id = :inst_id',
        params)
    executor.execute(
        f'DELETE FROM "{own_table}" '
        f'WHERE bk_asst_obj_id = :model_id AND bk_asst_inst_id = :inst_id',
        params)

    # 从对端模型分表清理冗余记录
    for item in related_dest:
        dest_model = item.get('bk_asst_obj_id')
        if dest_model and dest_model != bk_obj_id:
            dest_table = get_inst_asst_table_name(dest_model)
            try:
                executor.execute(
                    f'DELETE FROM "{dest_table}" '
                    f'WHERE bk_obj_id = :model_id AND bk_inst_id = :inst_id',
                    params)
            except Exception:
                pass
    for item in related_src:
        src_model = item.get('bk_obj_id')
        if src_model and src_model != bk_obj_id:
            src_table = get_inst_asst_table_name(src_model)
            try:
                executor.execute(
                    f'DELETE FROM "{src_table}" '
                    f'WHERE bk_asst_obj_id = :model_id AND bk_asst_inst_id = :inst_id',
                    params)
            except Exception:
                pass


def _mainline_descendant_module_ids(obj_id: str, inst_id: int,
                                    bk_biz_id: int, supplier_account: str) -> List[int]:
    """沿主线从当前节点向下，收集其下所有 module 实例 id（用于 hasHost 校验）。

    对齐上游 inst.hasHost 的 mainlineHasHost：沿主线子级递归定位所有下游模块。
    """
    from app.service.instance_service import InstanceService
    model_tree = get_mainline_model_top(supplier_account)
    levels = model_tree.leftest_object_id_list()
    if obj_id not in levels:
        return []
    idx = levels.index(obj_id)
    child_levels = levels[idx + 1:]
    if not child_levels:
        return []

    frontier = [inst_id]
    module_ids: List[int] = []
    for lvl in child_levels:
        if lvl == MAINLINE_MODEL_MODULE:
            module_ids = frontier
            break
        table = InstanceService._get_table_name(lvl)
        id_field = InstanceService._get_id_field(lvl)
        placeholders = ','.join(str(i) for i in frontier)
        rows = query_all(
            f'SELECT "{id_field}" FROM "{table}" '
            f'WHERE bk_supplier_account = :supplier AND bk_biz_id = :biz_id '
            f'AND "bk_parent_id" IN ({placeholders})',
            {'supplier': supplier_account, 'biz_id': bk_biz_id})
        frontier = [r[id_field] for r in rows]
        if not frontier:
            break
    return module_ids


def _collect_mainline_descendants(obj_id: str, inst_id: int,
                                  bk_biz_id: int, supplier_account: str) -> Dict[str, List[int]]:
    """沿主线从当前节点向下，递归收集其下所有子实例 id（不含自身），按模型层归类。

    用于自定义业务拓扑模型节点删除前的「下游非空」拦截校验：
    任一子层存在实例（set/module/其它自定义层）即视为非空，需先清空才能删除。
    对齐上游删除非叶子拓扑节点「非空即禁删」的一致性要求。
    """
    from app.service.instance_service import InstanceService

    model_tree = get_mainline_model_top(supplier_account)
    levels = model_tree.leftest_object_id_list()
    if obj_id not in levels:
        return {}
    idx = levels.index(obj_id)
    child_levels = levels[idx + 1:]
    if not child_levels:
        return {}

    result: Dict[str, List[int]] = {}
    frontier = [inst_id]
    for lvl in child_levels:
        if not frontier:
            break
        table = InstanceService._get_table_name(lvl)
        id_field = InstanceService._get_id_field(lvl)
        placeholders = ','.join(str(i) for i in frontier)
        rows = query_all(
            f'SELECT "{id_field}" FROM "{table}" '
            f'WHERE bk_supplier_account = :supplier AND bk_biz_id = :biz_id '
            f'AND "bk_parent_id" IN ({placeholders})',
            {'supplier': supplier_account, 'biz_id': bk_biz_id})
        ids = [r[id_field] for r in rows]
        if ids:
            result[lvl] = ids
        frontier = ids
    return result


def _delete_custom_mainline_node(bk_obj_id: str, bk_inst_id: int, bk_biz_id: int,
                                 supplier_account: str, executor) -> None:
    """自定义业务拓扑模型（自定义层级）节点删除：非空即拦截。

    对齐上游删除非叶子拓扑节点的一致性要求，删除前做四道校验，任一命中即拦截：
    1) 关联引用校验（被其它实例关联引用禁删）
    2) 下游模块挂主机校验（hasHost，有主机禁删）
    3) 下游存在集群(set)/模块(module)对象校验（非空即禁删）
    4) 下游存在其它自定义层子节点校验（非空即禁删）
    全部通过（下游子树为空）才删除自身并清理关联分表。对任意自定义层通用。
    """
    from app.service.instance_service import InstanceService
    from app.utils.exceptions import APIException, CCErrorCode

    model_tree = get_mainline_model_top(supplier_account)
    levels = model_tree.leftest_object_id_list()
    if bk_obj_id not in levels:
        raise ValueError(f'不支持的节点类型: {bk_obj_id}')

    # 1. 关联引用校验（被其它实例引用禁止删除）
    if _check_inst_associated(bk_obj_id, bk_inst_id):
        raise APIException('节点被其它实例关联引用, 不允许删除',
                           error_code=CCErrorCode.CCErrorTopoInstHasAssociation)

    # 2. 收集下游所有子实例（沿主线递归），用于主机/对象非空拦截校验
    descendants = _collect_mainline_descendants(bk_obj_id, bk_inst_id, bk_biz_id, supplier_account)
    set_ids = descendants.get(MAINLINE_MODEL_SET, [])
    module_ids = descendants.get(MAINLINE_MODEL_MODULE, [])
    other_ids = [i for lvl, ids in descendants.items()
                 if lvl not in (MAINLINE_MODEL_SET, MAINLINE_MODEL_MODULE) for i in ids]

    # 2a. 下挂主机校验：沿主线递归下游模块查主机，有则拦截（对齐上游 hasHost）
    if module_ids:
        placeholders = ','.join(str(m) for m in module_ids)
        host_count = query_one(
            f'SELECT COUNT(DISTINCT bk_host_id) as count FROM cc_ModuleHostConfig '
            f'WHERE bk_module_id IN ({placeholders})')
        if host_count and host_count['count'] > 0:
            raise APIException('节点下存在主机, 不允许删除',
                               error_code=CCErrorCode.CCErrTopoHasHostCheckFailed)

    # 2b. 下挂集群(set)对象校验：非空即拦截（需先清空下游才能删除）
    if set_ids:
        raise APIException(f'节点下存在集群(set)共 {len(set_ids)} 个, 不允许删除',
                           error_code=CCErrorCode.CCErrTopoHasChildNode)

    # 2c. 下挂模块(module)对象校验：非空即拦截
    if module_ids:
        raise APIException(f'节点下存在模块(module)共 {len(module_ids)} 个, 不允许删除',
                           error_code=CCErrorCode.CCErrTopoHasChildNode)

    # 2d. 下挂其它自定义层子节点校验：非空即拦截
    if other_ids:
        raise APIException(f'节点下存在子节点共 {len(other_ids)} 个, 不允许删除',
                           error_code=CCErrorCode.CCErrTopoHasChildNode)

    # 3. 下游为空（无任何 set/module/自定义层/主机）→ 删除自身 + 清理关联分表
    self_table = InstanceService._get_table_name(bk_obj_id)
    self_id_field = InstanceService._get_id_field(bk_obj_id)
    executor.execute(
        f'DELETE FROM "{self_table}" WHERE "{self_id_field}" = :inst_id AND bk_biz_id = :biz_id',
        {'inst_id': bk_inst_id, 'biz_id': bk_biz_id})
    # 清理自定义层实例关联分表（源+目标 + 对端冗余），与 set/module 对齐：
    # 关联记录双写于源/目标两张分表，必须一并清掉对端分表中的副本，
    # 否则 app_sys→其它实例 的关联会在对方分表留下悬挂孤儿。
    _clean_instance_associations(bk_obj_id, bk_inst_id, executor)


def delete_node(bk_obj_id: str, bk_inst_id: int,
                bk_biz_id: int = None, supplier_account: str = DEFAULT_SUPPLIER) -> None:
    """
    删除业务拓扑节点（biz/set/module 及自定义层级），与原项目删除冲突校验一致：

    - 业务(biz)：内置业务(default=1)禁删；业务下存在非空闲机池集群/模块(default!=1)禁删（空闲机池除外）
    - 集群(set)：集群下模块存在主机禁删；校验通过后级联删除集群下所有模块再删集群
    - 模块(module)：模块下存在主机禁删；模块被其它实例关联引用禁删
    - 自定义层级：沿主线递归下游模块查主机(有主机禁删)；被关联引用禁删；级联删下游再删自身

    Args:
        bk_obj_id: 节点类型（主线模型ID）
        bk_inst_id: 节点实例ID
        bk_biz_id: 业务ID（set/module/自定义层级时必填）
        supplier_account: 供应商账号
    """
    from app.utils.exceptions import APIException, CCErrorCode, NotFoundException
    from app.db.executor import SQLExecutor

    executor = SQLExecutor()

    if bk_obj_id == MAINLINE_MODEL_BIZ:
        # 1. 内置业务（资源池，default=1）禁止删除 —— 对齐上游 checkHasBuiltInBiz
        builtin = query_one(
            'SELECT COUNT(*) as count FROM cc_ApplicationBase '
            'WHERE bk_biz_id = :biz_id AND "default" = 1',
            {'biz_id': bk_inst_id})
        if builtin and builtin['count'] > 0:
            raise APIException('内置业务(资源池)不允许删除',
                               error_code=CCErrorCode.CCErrorTopoForbiddenDeleteBuiltInBiz)

        # 2. 业务下存在「非空闲机池」的集群/模块（default != 1）禁止删除
        #    空闲机池（default=1 的 set）视为业务内置骨架，不计入子节点校验，
        #    校验通过后会随业务一并级联清理，避免孤儿数据。
        child_set_count = query_one(
            'SELECT COUNT(*) as count FROM cc_SetBase '
            'WHERE bk_biz_id = :biz_id AND "default" != 1',
            {'biz_id': bk_inst_id})
        if child_set_count and child_set_count['count'] > 0:
            raise APIException(
                '业务下存在未删除的集群/模块节点（空闲机池除外），无法删除',
                error_code=CCErrorCode.CCErrTopoHasChildNode)

        # 3. 级联清理空闲机池（default set + 其内部模块 + 主机挂载），避免孤儿数据
        idle_modules = query_all(
            'SELECT bk_module_id FROM cc_ModuleBase '
            'WHERE bk_biz_id = :biz_id AND "default" != 0',
            {'biz_id': bk_inst_id})
        if idle_modules:
            idle_module_ids = ','.join(str(m['bk_module_id']) for m in idle_modules)
            executor.execute(
                f'DELETE FROM cc_ModuleHostConfig WHERE bk_module_id IN ({idle_module_ids})')
            executor.execute(
                f'DELETE FROM cc_ModuleBase WHERE bk_module_id IN ({idle_module_ids})')
        executor.execute(
            'DELETE FROM cc_SetBase WHERE bk_biz_id = :biz_id AND "default" = 1',
            {'biz_id': bk_inst_id})

        # 4. 清理业务自身的实例关联分表记录 —— 对齐 InstanceService.delete_instances
        from app.service.association_service import get_inst_asst_table_name
        biz_asst_table = get_inst_asst_table_name(MAINLINE_MODEL_BIZ)
        try:
            executor.execute(
                f'DELETE FROM "{biz_asst_table}" '
                f'WHERE bk_obj_id = :model AND bk_inst_id = :inst_id',
                {'model': MAINLINE_MODEL_BIZ, 'inst_id': bk_inst_id})
            executor.execute(
                f'DELETE FROM "{biz_asst_table}" '
                f'WHERE bk_asst_obj_id = :model AND bk_asst_inst_id = :inst_id',
                {'model': MAINLINE_MODEL_BIZ, 'inst_id': bk_inst_id})
        except Exception:
            pass

        # 5. 删除业务主表
        executor.execute(
            'DELETE FROM cc_ApplicationBase WHERE bk_biz_id = :biz_id',
            {'biz_id': bk_inst_id})

    elif bk_obj_id == MAINLINE_MODEL_SET:
        if not bk_biz_id:
            raise ValueError('删除集群需要 bk_biz_id')

        # 归属校验：集群必须确实属于该业务，避免 bk_biz_id 不匹配导致静默空删
        # （对齐上游：实例不存在于指定业务时返回 not found）
        owned = query_one(
            'SELECT COUNT(*) as count FROM cc_SetBase '
            'WHERE bk_set_id = :set_id AND bk_biz_id = :biz_id',
            {'set_id': bk_inst_id, 'biz_id': bk_biz_id})
        if not owned or owned['count'] == 0:
            raise NotFoundException(f'集群 {bk_inst_id} 不存在于业务 {bk_biz_id}')

        # 关联引用校验：集群被其它实例关联引用禁删（与 module 对齐，避免悬挂引用）
        if _check_inst_associated(MAINLINE_MODEL_SET, bk_inst_id):
            raise APIException('集群被其它实例关联引用, 不允许删除',
                               error_code=CCErrorCode.CCErrorTopoInstHasAssociation)

        # 复刻原项目 DeleteSet：先查集群下模块是否有关联主机
        module_ids = query_all(
            'SELECT bk_module_id FROM cc_ModuleBase '
            'WHERE bk_set_id = :set_id AND bk_biz_id = :biz_id',
            {'set_id': bk_inst_id, 'biz_id': bk_biz_id})
        if module_ids:
            module_id_list = [str(m['bk_module_id']) for m in module_ids]
            placeholders = ','.join(module_id_list)
            host_count = query_one(
                f'SELECT COUNT(DISTINCT bk_host_id) as count FROM cc_ModuleHostConfig '
                f'WHERE bk_module_id IN ({placeholders})')
            if host_count and host_count['count'] > 0:
                raise APIException('目标包含主机, 不允许删除',
                                   error_code=CCErrorCode.CCErrTopoHasHostCheckFailed)

        # 对齐上游 DeleteSet：先级联删除集群下的所有模块，再删除集群本身，避免孤儿模块。
        # 级联删除的模块同样需清理其关联分表（模块可能作为源持有 module→其它实例 的关联）。
        if module_ids:
            for m in module_ids:
                _clean_instance_associations(
                    MAINLINE_MODEL_MODULE, m['bk_module_id'], executor)
            executor.execute(
                'DELETE FROM cc_ModuleBase WHERE bk_set_id = :set_id AND bk_biz_id = :biz_id',
                {'set_id': bk_inst_id, 'biz_id': bk_biz_id})

        # 清理集群自身的实例关联分表（源+目标 + 对端冗余），避免悬挂孤儿关联
        _clean_instance_associations(MAINLINE_MODEL_SET, bk_inst_id, executor)

        executor.execute(
            'DELETE FROM cc_SetBase WHERE bk_set_id = :set_id AND bk_biz_id = :biz_id',
            {'set_id': bk_inst_id, 'biz_id': bk_biz_id})

    elif bk_obj_id == MAINLINE_MODEL_MODULE:
        if not bk_biz_id:
            raise ValueError('删除模块需要 bk_biz_id')

        # 归属校验：模块必须确实属于该业务，避免 bk_biz_id 不匹配导致静默空删
        owned = query_one(
            'SELECT COUNT(*) as count FROM cc_ModuleBase '
            'WHERE bk_module_id = :module_id AND bk_biz_id = :bk_biz_id',
            {'module_id': bk_inst_id, 'bk_biz_id': bk_biz_id})
        if not owned or owned['count'] == 0:
            raise NotFoundException(f'模块 {bk_inst_id} 不存在于业务 {bk_biz_id}')

        # 复刻原项目 DeleteModule：模块下存在主机禁止删除
        host_count = query_one(
            'SELECT COUNT(*) as count FROM cc_ModuleHostConfig WHERE bk_module_id = :module_id',
            {'module_id': bk_inst_id})
        if host_count and host_count['count'] > 0:
            raise APIException('目标包含主机, 不允许删除',
                               error_code=CCErrorCode.CCErrTopoHasHostCheckFailed)

        # 对齐上游 deleteInsts 的 CheckAssociations：模块被其它实例关联引用禁止删除
        if _check_inst_associated(MAINLINE_MODEL_MODULE, bk_inst_id):
            raise APIException('模块被其它实例关联引用, 不允许删除',
                               error_code=CCErrorCode.CCErrorTopoInstHasAssociation)

        # 清理模块关联分表（源+目标 + 对端冗余），避免删除后留下 module→其它实例 的悬挂孤儿关联
        _clean_instance_associations(MAINLINE_MODEL_MODULE, bk_inst_id, executor)

        executor.execute(
            'DELETE FROM cc_ModuleBase WHERE bk_module_id = :module_id AND bk_biz_id = :bk_biz_id',
            {'module_id': bk_inst_id, 'bk_biz_id': bk_biz_id})

    else:
        # 自定义业务拓扑模型（自定义层级）节点删除
        # 对齐上游通用 DeleteInst：hasHost(沿主线递归下游模块查主机) + 关联引用校验
        # + 级联删下游 + 删自身
        _delete_custom_mainline_node(bk_obj_id, bk_inst_id, bk_biz_id, supplier_account, executor)
