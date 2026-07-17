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

# 主线模型中文名（前端树节点 bk_obj_name 使用）
OBJ_NAME_MAP = {
    'biz': '业务',
    'set': '集群',
    'module': '模块',
}


def get_business_module_topo(bk_biz_id: int,
                             supplier_account: str = DEFAULT_SUPPLIER) -> List[Dict[str, Any]]:
    """
    获取转移"业务模块"所需的业务拓扑树（集群分类 + 模块分类，含 default 标识）。

    对应原项目 getInstTopo（POST find/topoinst/biz/{bizId}）。

    返回结构（与前端 bk-big-tree 节点 options 匹配）：
    [
      {
        "bk_obj_id": "biz",
        "bk_inst_id": <biz_id>,
        "bk_inst_name": "<业务名>",
        "bk_obj_name": "业务",
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

    其中 default 字段用于区分"集群分类"与"模块分类"：
    - set 级 default=1 即空闲机池（集群分类的特殊类）
    - module 级 default>=1 即内部模块（空闲机/故障机/待回收）

    Args:
        bk_biz_id: 业务ID
        supplier_account: 供应商账号，默认 '0'

    Returns:
        业务拓扑树数组（仅含一个业务根节点）
    """
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

    set_rows = query_all(
        """
        SELECT bk_set_id, bk_set_name, "default"
        FROM cc_SetBase
        WHERE bk_biz_id = :bk_biz_id
          AND bk_supplier_account = :supplier
        ORDER BY "default" DESC, bk_set_id
        """,
        {'bk_biz_id': bk_biz_id, 'supplier': supplier_account}
    )

    module_rows = query_all(
        """
        SELECT bk_module_id, bk_module_name, bk_set_id, "default"
        FROM cc_ModuleBase
        WHERE bk_biz_id = :bk_biz_id
          AND bk_supplier_account = :supplier
        ORDER BY "default" DESC, bk_module_id
        """,
        {'bk_biz_id': bk_biz_id, 'supplier': supplier_account}
    )

    # 各模块主机数（来自 cc_ModuleHostConfig 绑定，作为模块分类的上下文）
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

    # 按 set 归并模块（模块分类）
    modules_by_set: Dict[int, List[Dict[str, Any]]] = {}
    for m in module_rows:
        sid = m['bk_set_id']
        modules_by_set.setdefault(sid, []).append({
            'bk_obj_id': 'module',
            'bk_inst_id': m['bk_module_id'],
            'bk_inst_name': m['bk_module_name'],
            'bk_obj_name': OBJ_NAME_MAP['module'],
            'default': m['default'] or 0,
            'host_count': host_count_map.get(m['bk_module_id'], 0),
        })

    # 组装集群分类
    children = []
    for s in set_rows:
        sid = s['bk_set_id']
        children.append({
            'bk_obj_id': 'set',
            'bk_inst_id': sid,
            'bk_inst_name': s['bk_set_name'],
            'bk_obj_name': OBJ_NAME_MAP['set'],
            'default': s['default'] or 0,
            'child': modules_by_set.get(sid, []),
        })

    return [{
        'bk_obj_id': 'biz',
        'bk_inst_id': bk_biz_id,
        'bk_inst_name': biz['bk_biz_name'],
        'bk_obj_name': OBJ_NAME_MAP['biz'],
        'default': 0,
        'child': children,
    }]


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

    for host_id in host_ids:
        # 单主机：删除全部旧绑定 -> 插入新目标绑定 -> 回退保护，包裹在同一事务内保证原子性
        def _do_transfer(conn):
            conn.execute(
                text('DELETE FROM cc_ModuleHostConfig WHERE bk_biz_id = :biz AND bk_host_id = :host'),
                {'biz': bk_biz_id, 'host': host_id}
            )
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
            # 回退保护：用同一事务连接查询（可见未提交插入），若已无任何绑定则挂空闲机
            remain = conn.execute(
                text('SELECT 1 FROM cc_ModuleHostConfig WHERE bk_biz_id = :biz AND bk_host_id = :host LIMIT 1'),
                {'biz': bk_biz_id, 'host': host_id}
            ).fetchone()
            if not remain:
                idle = query_one(
                    """
                    SELECT m.bk_module_id AS mid, m.bk_set_id AS sid
                    FROM cc_ModuleBase m
                    JOIN cc_SetBase s
                      ON m.bk_biz_id = s.bk_biz_id AND m.bk_set_id = s.bk_set_id
                    WHERE m.bk_biz_id = :biz AND m."default" = 1 AND s."default" = 1
                    LIMIT 1
                    """,
                    {'biz': bk_biz_id}
                )
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

        sql_executor.transaction([_do_transfer])

    return {
        'transferrd_hosts': len(host_ids),
        'target_modules': module_ids,
        'transfer_type': transfer_type,
    }
