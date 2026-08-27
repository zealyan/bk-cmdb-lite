"""
主机转移（转移到业务模块 / 空闲机池）服务

对应原项目：
- src/ui/src/store/modules/api/object-main-line-module.js
    - getInstTopo:    POST find/topoinst/biz/{bizId}
    - getInternalTopo: GET topo/internal/{supplierAccount}/{bizId}/with_statistics
- src/source_controller/coreservice/core/host/transfer/

核心数据表：
- cc_ApplicationBase / cc_SetBase / cc_ModuleBase : 主线拓扑实例
- cc_ModuleHostConfig : 主机-模块绑定关系
    default 字段语义：0 普通业务模块 / 1 空闲机 / 2 故障机 / 3 待回收
    空闲机池 = default=1 的"集群(set)"，其下包含 default>=1 的内部模块
"""
from typing import Dict, List, Any, Optional

from app.db.executor import query_all, query_one, sql_executor

DEFAULT_SUPPLIER = '0'

# 主线模型中文名（前端树节点 bk_obj_name 兜底；优先取 cc_ObjDes 实际模型名）
OBJ_NAME_MAP = {
    'biz': '业务',
    'set': '集群',
    'module': '模块',
}


def _get_obj_name_map(supplier_account: str = DEFAULT_SUPPLIER) -> Dict[str, str]:
    """
    构建 obj_id -> bk_obj_name（中文名）映射，含自定义主线模型（appsys/zone...）。

    来源 cc_ObjDes（bk_obj_id, bk_obj_name）；内置 biz/set/module 以 OBJ_NAME_MAP 兜底。
    """
    name_map = dict(OBJ_NAME_MAP)
    try:
        rows = query_all(
            "SELECT bk_obj_id, bk_obj_name FROM cc_ObjDes "
            "WHERE bk_supplier_account = :sup",
            {'sup': supplier_account})
        for r in rows:
            if r['bk_obj_name']:
                name_map[r['bk_obj_id']] = r['bk_obj_name']
    except Exception:
        # cc_ObjDes 缺失时仅用兜底映射，自定义层退化为 obj_id 自身
        pass
    return name_map


def get_business_module_topo(bk_biz_id: int,
                             supplier_account: str = DEFAULT_SUPPLIER) -> List[Dict[str, Any]]:
    """
    获取转移"业务模块"所需的业务拓扑树（集群分类 + 模块分类，含 default 标识）。

    对应原项目 getInstTopo（POST find/topoinst/biz/{bizId}）。

    与原 lite 旧实现差异（对齐上游自定义主线）：
    - 旧实现写死 biz -> set -> module，直接按 bk_biz_id 平铺 cc_SetBase/cc_ModuleBase，
      完全忽略 bk_parent_id 与自定义主线层（appsys/zone），导致迁移框里查不到
      appsys 层级、set/module 被错误挂到 biz 下。
    - 新实现复用主线模型顺序（get_mainline_model_top().leftest_object_id_list()），
      按 bk_parent_id 逐层拼装实例树，自动纳入任意自定义主线层：
          biz -> [appsys] -> ... -> set -> module
      每个节点都带 bk_obj_name（来自 cc_ObjDes），module 带 host_count。

    返回结构（与前端 bk-big-tree 节点 options 匹配）：
    [
      {
        "bk_obj_id": "biz",
        "bk_inst_id": <biz_id>,
        "bk_inst_name": "<业务名>",
        "bk_obj_name": "业务",
        "default": 0,
        "child": [
          {                                   # 自定义主线层（appsys 等），自动出现
            "bk_obj_id": "appsys",
            "bk_inst_id": <appsys_id>,
            "bk_inst_name": "<应用系统名>",
            "bk_obj_name": "应用系统",
            "default": 0,
            "child": [
              {
                "bk_obj_id": "set",
                "bk_inst_id": <set_id>,
                "bk_inst_name": "<集群名>",
                "bk_obj_name": "集群",
                "default": 0,                  # 1 表示空闲机池(set)
                "child": [
                  {
                    "bk_obj_id": "module",
                    "bk_inst_id": <module_id>,
                    "bk_inst_name": "<模块名>",
                    "bk_obj_name": "模块",
                    "default": 0,              # 0 普通 / 1 空闲机 / 2 故障机 / 3 待回收
                    "host_count": <该模块主机数>
                  }
                ]
              }
            ]
          }
        ]
      }
    ]

    其中 default 字段用于区分"集群分类"与"模块分类"：
    - set 级 default=1 即空闲机池（集群分类的特殊类）
    - module 级 default>=1 即内部模块（空闲机/故障机/待回收）

    Args:
        bk_biz_id: 业务ID
        supplier_account: 供应商账号，默认 '0'

    Returns:
        业务拓扑树数组（仅含一个业务根节点）
    """
    from app.service import topo_service

    biz = query_one(
        """
        SELECT bk_biz_id, bk_biz_name
        FROM cc_ApplicationBase
        WHERE bk_biz_id = :bk_biz_id
          AND bk_supplier_account = :supplier
        """,
        {'bk_biz_id': bk_biz_id, 'supplier': supplier_account}
    )
    if not biz:
        return []

    # 主线模型顺序：biz -> appsys -> ... -> set -> module（自定义层自动纳入）
    model_levels = topo_service.get_mainline_model_top(supplier_account).leftest_object_id_list()
    name_map = _get_obj_name_map(supplier_account)

    # 各模块主机数（来自 cc_ModuleHostConfig 绑定）
    host_count_rows = query_all(
        """
        SELECT bk_module_id, COUNT(DISTINCT bk_host_id) AS host_count
        FROM cc_ModuleHostConfig
        WHERE bk_biz_id = :bk_biz_id
          AND bk_supplier_account = :supplier
        GROUP BY bk_module_id
        """,
        {'bk_biz_id': bk_biz_id, 'supplier': supplier_account}
    )
    host_count_map = {r['bk_module_id']: r['host_count'] for r in host_count_rows}

    # 加载每个主线程层的全部实例（通用，内置/自定义统一）
    level_insts: Dict[str, List[Dict[str, Any]]] = {}
    for lvl in model_levels:
        level_insts[lvl] = topo_service._load_mainline_level(lvl, bk_biz_id, supplier_account)

    # 构建节点（暂存直接父实例 _pid，供后续按主线父链拼装）
    nodes: Dict[str, Dict[int, Dict[str, Any]]] = {lvl: {} for lvl in model_levels}
    for lvl in model_levels:
        id_field = topo_service.model_id_field(lvl)
        name_field = topo_service.model_name_field(lvl)
        for inst in level_insts[lvl]:
            iid = inst[id_field]
            nodes[lvl][iid] = {
                'bk_obj_id': lvl,
                'bk_inst_id': iid,
                'bk_inst_name': inst.get(name_field, f'{lvl}_{iid}'),
                'bk_obj_name': name_map.get(lvl, lvl),
                'default': inst.get('default', 0) or 0,
                '_pid': inst.get('bk_parent_id') or 0,
                'child': [],
            }

    # 业务根节点
    root = nodes[model_levels[0]].get(bk_biz_id)
    if root is None:
        root = {
            'bk_obj_id': 'biz',
            'bk_inst_id': bk_biz_id,
            'bk_inst_name': biz['bk_biz_name'],
            'bk_obj_name': name_map.get('biz', OBJ_NAME_MAP['biz']),
            'default': 0,
            '_pid': 0,
            'child': [],
        }
        nodes[model_levels[0]][bk_biz_id] = root

    # 逐层按 bk_parent_id 挂到直接父节点（支持任意多自定义层）
    for idx in range(1, len(model_levels)):
        lvl = model_levels[idx]
        parent_lvl = model_levels[idx - 1]
        parent_nodes = nodes[parent_lvl]
        for node in nodes[lvl].values():
            pid = node.pop('_pid', 0)
            parent = parent_nodes.get(pid)
            if parent is not None:
                parent['child'].append(node)
            else:
                # 孤儿实例（父缺失）：挂到业务根，保证可见，不参与统计聚合
                root['child'].append(node)

    # 模块层补充主机数（module 是主线叶子，无更深层子节点）
    module_lvl = topo_service.MAINLINE_MODEL_MODULE
    if module_lvl in nodes:
        for node in nodes[module_lvl].values():
            node['host_count'] = host_count_map.get(node['bk_inst_id'], 0)

    return [root]


def get_idle_pool(bk_biz_id: int,
                  supplier_account: str = DEFAULT_SUPPLIER) -> Dict[str, Any]:
    """
    获取空闲机池（转移到空闲模块所需）。

    对应原项目 getInternalTopo（GET topo/internal/{supplierAccount}/{bizId}/with_statistics）。

    空闲机池 = default=1 的"集群(set)"，其下包含 default>=1 的内部模块：
        1 空闲机 / 2 故障机 / 3 待回收。

    Returns:
        {
          "bk_set_id": <空闲机池 set id>,
          "bk_set_name": "<空闲机池名>",
          "module": [
            {"bk_module_id":..., "bk_module_name":..., "default": 1},
            ...
          ]
        }
    """
    idle_set = query_one(
        """
        SELECT bk_set_id, bk_set_name
        FROM cc_SetBase
        WHERE bk_biz_id = :bk_biz_id
          AND bk_supplier_account = :supplier
          AND "default" = 1
        LIMIT 1
        """,
        {'bk_biz_id': bk_biz_id, 'supplier': supplier_account}
    )
    if not idle_set:
        return {'bk_set_id': None, 'bk_set_name': '', 'module': []}

    modules = query_all(
        """
        SELECT bk_module_id, bk_module_name, "default"
        FROM cc_ModuleBase
        WHERE bk_biz_id = :bk_biz_id
          AND bk_supplier_account = :supplier
          AND bk_set_id = :bk_set_id
          AND "default" >= 1
        ORDER BY "default", bk_module_id
        """,
        {'bk_biz_id': bk_biz_id, 'supplier': supplier_account,
         'bk_set_id': idle_set['bk_set_id']}
    )
    module_list = [{
        'bk_module_id': m['bk_module_id'],
        'bk_module_name': m['bk_module_name'],
        'default': m['default'] or 0,
    } for m in modules]

    return {
        'bk_set_id': idle_set['bk_set_id'],
        'bk_set_name': idle_set['bk_set_name'],
        'module': module_list,
    }


def get_host_module_config(bk_biz_id: int,
                           host_ids: Optional[List[int]] = None,
                           supplier_account: str = DEFAULT_SUPPLIER) -> List[Dict[str, Any]]:
    """
    查询指定主机在当前业务下的模块绑定关系（来自 cc_ModuleHostConfig）。

    用于转移前预选主机当前所属模块，也作为后续"写操作"的上下文依据
    （删除原绑定 + 写入新绑定）。

    Args:
        bk_biz_id: 业务ID
        host_ids: 主机ID列表（为空则返回该业务全部绑定）
        supplier_account: 供应商账号，默认 '0'

    Returns:
        [
          {"bk_host_id":..., "bk_module_id":..., "bk_set_id":...,
           "bk_biz_id":..., "bk_supplier_account":...},
          ...
        ]
    """
    host_ids = host_ids or []

    if host_ids:
        placeholders = ', '.join([f":hid_{i}" for i in range(len(host_ids))])
        where_host = f"AND bk_host_id IN ({placeholders})"
        params = {'bk_biz_id': bk_biz_id, 'supplier': supplier_account}
        for i, hid in enumerate(host_ids):
            params[f'hid_{i}'] = hid
    else:
        where_host = ""
        params = {'bk_biz_id': bk_biz_id, 'supplier': supplier_account}

    rows = query_all(
        f"""
        SELECT bk_host_id, bk_module_id, bk_set_id, bk_biz_id, bk_supplier_account
        FROM cc_ModuleHostConfig
        WHERE bk_biz_id = :bk_biz_id
          AND bk_supplier_account = :supplier
          {where_host}
        ORDER BY bk_host_id, bk_module_id
        """,
        params
    )
    return [dict(r) for r in rows]


def transfer_modules(bk_biz_id: int,
                     supplier_account: str,
                     host_ids: List[int],
                     module_ids: List[int],
                     transfer_type: str) -> Dict[str, Any]:
    """
    执行主机转移写操作（修改 cc_ModuleHostConfig 绑定关系）。

    语义（与用户确认的"清除全部绑定"策略一致）：
    - 无论转移到业务模块还是空闲模块，均先删除该主机在业务内的**全部**旧模块绑定，
      再写入新选的目标模块绑定（进入普通业务模块即离开空闲机池；反之亦然）。
    - 回退保护（防御性）：若写入后该主机在业务内已无任何模块绑定（理论不会发生），
      自动挂到"空闲机(default=1)"模块，保证主机至少归属一个模块。
    - 批次原子性：全部 host 的转移在同一事务内完成（单一 conn.begin()），
      任一主机失败整批回滚，不存在"前 N-1 台已提交"的撕裂状态。

    Args:
        bk_biz_id: 业务ID
        supplier_account: 供应商账号
        host_ids: 待转移主机ID列表（非空）
        module_ids: 目标模块ID列表（非空）
        transfer_type: 'business'（业务模块，目标 default=0）/ 'idle'（空闲模块，目标 default>=1）

    Returns:
        { 'transferrd_hosts': N, 'target_modules': [...], 'transfer_type': ... }

    Raises:
        ValueError: 参数非法 / 目标模块不属于该业务 / 目标模块类型与 transfer_type 不匹配
    """
    from sqlalchemy import text

    if transfer_type not in ('idle', 'business'):
        raise ValueError(f'不支持的转移类型: {transfer_type}')
    if not host_ids:
        raise ValueError('主机ID列表不能为空')
    if not module_ids:
        raise ValueError('目标模块列表不能为空')

    # 解析并校验目标模块（必须属于该业务，且类型与 transfer_type 匹配）
    placeholders = ', '.join([f':mid_{i}' for i in range(len(module_ids))])
    params = {f'mid_{i}': mid for i, mid in enumerate(module_ids)}
    params['biz'] = bk_biz_id
    target_rows = query_all(
        f"""
        SELECT bk_module_id, bk_set_id, "default", bk_biz_id AS module_biz
        FROM cc_ModuleBase
        WHERE bk_biz_id = :biz AND bk_module_id IN ({placeholders})
        """,
        params
    )
    found_ids = {r['bk_module_id'] for r in target_rows}
    invalid = [mid for mid in module_ids if mid not in found_ids]
    if invalid:
        raise ValueError(f'以下模块不存在或不属于业务 {bk_biz_id}: {invalid}')

    if transfer_type == 'idle':
        bad = [r['bk_module_id'] for r in target_rows if (r['default'] or 0) < 1]
        if bad:
            raise ValueError(f'空闲模块转移目标必须为空闲机/故障机/待回收(default>=1): {bad}')
    else:
        bad = [r['bk_module_id'] for r in target_rows if (r['default'] or 0) != 0]
        if bad:
            raise ValueError(f'业务模块转移目标必须为普通模块(default=0): {bad}')

    valid_modules = [
        {'bk_module_id': r['bk_module_id'], 'bk_set_id': r['bk_set_id']}
        for r in target_rows
    ]

    # 批次原子性：整个 host 列表放入【单一事务】（一个 conn.begin() 内跑完全部主机），
    # 任一主机失败则全批回滚，避免旧实现"每主机一事务"导致前 N-1 台已提交、中途失败
    # 产生撕裂状态。语义对齐原项目 bk-cmdb（coreservice genericTransfer.Transfer：
    # 先整批 Delete 再整批 Insert，无逐主机事务）。
    def _do_transfer_batch(conn):
        for host_id in host_ids:
            # 单主机：删除全部旧绑定
            conn.execute(
                text('DELETE FROM cc_ModuleHostConfig WHERE bk_biz_id = :biz AND bk_host_id = :host'),
                {'biz': bk_biz_id, 'host': host_id}
            )
            # 写入新目标绑定
            for m in valid_modules:
                conn.execute(
                    text(
                        'INSERT INTO cc_ModuleHostConfig '
                        '(bk_biz_id, bk_host_id, bk_module_id, bk_set_id, bk_supplier_account) '
                        'VALUES (:biz, :host, :mid, :sid, :supplier)'
                    ),
                    {
                        'biz': bk_biz_id,
                        'host': host_id,
                        'mid': m['bk_module_id'],
                        'sid': m['bk_set_id'],
                        'supplier': supplier_account,
                    }
                )
            # 回退保护：用同一事务连接查询（可见未提交插入），若已无任何绑定则挂空闲机。
            # 注意必须用 conn（事务内连接）而非全局 query_one，否则读不到本事务未提交数据。
            remain = conn.execute(
                text('SELECT 1 FROM cc_ModuleHostConfig WHERE bk_biz_id = :biz AND bk_host_id = :host LIMIT 1'),
                {'biz': bk_biz_id, 'host': host_id}
            ).fetchone()
            if not remain:
                idle = conn.execute(
                    text(
                        """
                        SELECT m.bk_module_id AS mid, m.bk_set_id AS sid
                        FROM cc_ModuleBase m
                        JOIN cc_SetBase s
                          ON m.bk_biz_id = s.bk_biz_id AND m.bk_set_id = s.bk_set_id
                        WHERE m.bk_biz_id = :biz AND m."default" = 1 AND s."default" = 1
                        LIMIT 1
                        """
                    ),
                    {'biz': bk_biz_id}
                ).fetchone()
                if idle:
                    conn.execute(
                        text(
                            'INSERT INTO cc_ModuleHostConfig '
                            '(bk_biz_id, bk_host_id, bk_module_id, bk_set_id, bk_supplier_account) '
                            'VALUES (:biz, :host, :mid, :sid, :supplier)'
                        ),
                        {
                            'biz': bk_biz_id,
                            'host': host_id,
                            'mid': idle['mid'],
                            'sid': idle['sid'],
                            'supplier': supplier_account,
                        }
                    )

    sql_executor.transaction([_do_transfer_batch])

    # 转移改变主机-模块绑定，失效 biz-topo 缓存（树节点 host_count 统计源）。
    # 否则批量统计接口（GetTopoNodeHostAndSerInstCount → _get_cached_topo）在
    # 60s TTL 内仍返回转移前的旧统计，导致前端刷新后节点统计不更新。
    from app.service.topo_service import clear_topo_cache
    clear_topo_cache(bk_biz_id, supplier_account)

    return {
        'transferrd_hosts': len(host_ids),
        'target_modules': module_ids,
        'transfer_type': transfer_type,
    }


def transfer_across_biz(src_biz_id: int,
                        dst_biz_id: int,
                        host_ids: List[int],
                        module_ids: List[int],
                        supplier_account: str = DEFAULT_SUPPLIER) -> Dict[str, Any]:
    """
    跨业务主机转移（源业务 A → 目标业务 B 的指定模块）。

    对齐原项目 POST /hosts/modules/across/biz（TransferHostAcrossBusiness）：
    解除源业务下这些主机的【全部】模块绑定，再在目标业务指定模块建立绑定。
    绑定记录归属随目标业务：写入时 cc_ModuleHostConfig.bk_biz_id = dst_biz_id。

    语义约束（与用户确认，不实现主机池）：
    - 删除源业务绑定时天然带 bk_biz_id=src，即「主机确实归属源业务」；
    - 不强制 module.default>=1（空闲机池）校验；
    - 目标模块须全部属于 dst_biz_id，否则拒绝（防跨业务模块混用）；
    - 批次原子性：全部 host 的转移在同一事务内完成（单一 conn.begin()），
      任一主机失败整批回滚。

    Args:
        src_biz_id: 源业务ID（主机当前所属业务）
        dst_biz_id: 目标业务ID（主机转移后的归属业务）
        host_ids: 待转移主机ID列表（非空）
        module_ids: 目标业务下的目标模块ID列表（非空）
        supplier_account: 供应商账号，默认 '0'

    Returns:
        { 'translators': ..., 'transferrd_hosts': N, 'target_biz': dst_biz_id, 'target_modules': [...] }

    Raises:
        ValueError: 参数非法 / 源业务与目标业务相同 / 目标模块不存在或不属于目标业务
    """
    from sqlalchemy import text

    if src_biz_id == dst_biz_id:
        raise ValueError('源业务与目标业务不能相同')
    if not host_ids:
        raise ValueError('主机ID列表不能为空')
    if not module_ids:
        raise ValueError('目标模块列表不能为空')

    # 校验目标模块全部属于 dst_biz_id（拒绝跨业务模块混用）
    placeholders = ', '.join([f':mid_{i}' for i in range(len(module_ids))])
    params = {f'mid_{i}': mid for i, mid in enumerate(module_ids)}
    params['dst'] = dst_biz_id
    target_rows = query_all(
        f"""
        SELECT bk_module_id, bk_set_id, "default", bk_biz_id AS module_biz
        FROM cc_ModuleBase
        WHERE bk_biz_id = :dst AND bk_module_id IN ({placeholders})
        """,
        params
    )
    found_ids = {r['bk_module_id'] for r in target_rows}
    invalid = [mid for mid in module_ids if mid not in found_ids]
    if invalid:
        raise ValueError(f'以下模块不存在或不属于目标业务 {dst_biz_id}: {invalid}')

    valid_modules = [
        {'bk_module_id': r['bk_module_id'], 'bk_set_id': r['bk_set_id']}
        for r in target_rows
    ]

    # 批次原子性：整个 host 列表放入【单一事务】，任一主机失败全批回滚，
    # 避免旧实现"每主机一事务"导致的批次撕裂；绑定记录的 bk_biz_id 写为目标业务。
    def _do_transfer_batch(conn):
        for host_id in host_ids:
            conn.execute(
                text('DELETE FROM cc_ModuleHostConfig WHERE bk_biz_id = :src AND bk_host_id = :host'),
                {'src': src_biz_id, 'host': host_id}
            )
            for m in valid_modules:
                conn.execute(
                    text(
                        'INSERT INTO cc_ModuleHostConfig '
                        '(bk_biz_id, bk_host_id, bk_module_id, bk_set_id, bk_supplier_account) '
                        'VALUES (:dst, :host, :mid, :sid, :supplier)'
                    ),
                    {
                        'dst': dst_biz_id,
                        'host': host_id,
                        'mid': m['bk_module_id'],
                        'sid': m['bk_set_id'],
                        'supplier': supplier_account,
                    }
                )

    sql_executor.transaction([_do_transfer_batch])

    # 跨业务转移同时改变源/目标业务的主机-模块绑定，一并失效两侧 biz-topo 缓存，
    # 否则批量统计接口在 TTL 内返回旧值，两侧拓扑树节点统计均不更新。
    from app.service.topo_service import clear_topo_cache
    clear_topo_cache(src_biz_id, supplier_account)
    clear_topo_cache(dst_biz_id, supplier_account)

    return {
        'transferrd_hosts': len(host_ids),
        'target_biz': dst_biz_id,
        'target_modules': module_ids,
    }
