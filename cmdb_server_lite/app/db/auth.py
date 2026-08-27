"""
鉴权（用户 + 策略）公共数据访问层。

设计要点（与 app/db/user.py 完全一致，作为鉴权领域的「单一真相源」）：
- 多方言：SQL 以 PostgreSQL 规范方言书写于 app/sql/auth/*.sql，运行时由
  app.db.dialect 转译到当前数据库方言（settings.DATABASE_TYPE），再经
  app.db.executor（SQLAlchemy text 参数化）执行。切换 SQLite / PostgreSQL / MySQL
  无需改代码，只改配置。
- 公共复用：后端 API（app/api/v1/auth_manage.py）与 CLI（app/cli/auth_cmd.py）
  均调用本模块，不各自拼 SQL，避免方言 / 权限语义漂移。
- 用户操作委托 app/db/user.py（同一套 werkzeug 哈希 + 列名 + 方言逻辑）。

表：
  cc_UserBase   用户表（列名对齐上游 cc_User）
  cc_AuthPolicy 策略表（supplier / principal / res_type / obj_id / action / effect）
                仅 'allow' 一种 effect（默认拒绝、策略允许，无 deny）。
"""

from typing import List, Dict, Any, Optional

from app.db.executor import SQLExecutor
from app.db.sql_loader import load_sql
from app.db.dialect import dialect_converter
from app.config.settings import get_config, DialectType

# 用户操作委托给公共用户层（保持密码哈希 / 列名 / 方言单一来源）
from app.db.user import (
    ROLE_ADMIN, ROLE_NORMAL,
    create_user as _create_user,
    get_user as _get_user,
    list_users as _list_users,
    exists_user as _exists_user,
    update_user_password as _update_user_password,
)

POLICY_TABLE = 'cc_AuthPolicy'
RES_TYPE_MODEL_INSTANCE = 'modelInstance'  # 模型实例（解析器产出，受网关拦截）
RES_TYPE_HOST_INSTANCE = 'hostInstance'   # 主机实例（含主机转移 transfer，受网关拦截）
RES_TYPE_BUSINESS = 'business'            # 业务（reserved：解析器暂未产出，网关不拦截）
RES_TYPE_BIZ_TOPOLOGY = 'biz_topology'    # 集群/模块/主线实例（解析器产出，受网关拦截）
RES_TYPE_MODEL = 'model'                  # 模型（reserved：解析器暂未产出，网关不拦截）
EFFECT_ALLOW = 'allow'

# SQL 文件书写所用的规范方言（DialectType.POSTGRESQL = 'postgres'）
_SOURCE_DIALECT = DialectType.POSTGRESQL.value

# 合法动作集合（与文档 §七 / §十 对齐）
# - 模型实例：create/update/delete/find
# - 业务拓扑：create/update/delete（作用于 biz_topology 资源）
# - 主机转移：transfer（与主机 update 区分；见 docs/权限设计方案.md §十）
VALID_ACTIONS = ('create', 'update', 'delete', 'find', 'transfer')

# 合法资源类型集合（值与 app.auth.resource.ResourceType 保持一致）。
# - modelInstance / hostInstance / biz_topology 是解析器实际产出、受网关拦截的类型；
# - business / model 为上游既有类型，lite 当前路由未暴露其写端点，解析器暂不产出，
#   故网关不拦截（reserved）。保留在白名单内以便将来接线路由，但分配给它们的策略
#   在当前版本不会被任何请求命中（写库无害、只是不生效）。
VALID_RES_TYPES = (
    RES_TYPE_MODEL_INSTANCE,
    RES_TYPE_HOST_INSTANCE,
    RES_TYPE_BUSINESS,
    RES_TYPE_BIZ_TOPOLOGY,
    RES_TYPE_MODEL,
)

# 资源类型 → 说明（CLI `res-type list` 单一来源；含"当前是否受网关拦截"状态）
RES_TYPE_DESCRIPTIONS = {
    RES_TYPE_MODEL_INSTANCE: '模型实例：create/update/delete/find（业务拓扑外的模型 CRUD，受网关拦截）',
    RES_TYPE_HOST_INSTANCE:  '主机实例：transfer=主机转移（与主机 update 解耦，受网关拦截）',
    RES_TYPE_BUSINESS:       '业务（reserved：当前路由未暴露业务级写，网关暂不拦截）',
    RES_TYPE_BIZ_TOPOLOGY:   '集群/模块/主线实例：create/update/delete（上游 IAM 统一映射，受网关拦截）',
    RES_TYPE_MODEL:          '模型（reserved：模型元数据管理，解析器未产出该类型，网关暂不拦截）',
}


def _validate_res_type(res_type: str) -> None:
    """校验资源类型合法性，非法则抛 ValueError（与 _validate_action 风格一致）。"""
    if res_type not in VALID_RES_TYPES:
        raise ValueError(f'非法资源类型: {res_type}（仅 {VALID_RES_TYPES}）')


# ---------------------------------------------------------------------------
# 多方言核心
# ---------------------------------------------------------------------------
def _target_dialect() -> str:
    """当前数据库方言（sqlglot 书写名）。"""
    return {
        'sqlite': DialectType.SQLITE.value,         # 'sqlite'
        'postgresql': DialectType.POSTGRESQL.value,  # 'postgres'
        'mysql': DialectType.MYSQL.value,           # 'mysql'
    }.get(get_config().DATABASE_TYPE, DialectType.SQLITE.value)


def _sql(filename: str) -> str:
    """加载 SQL 文件并转译到当前方言（多方言核心）。"""
    raw = load_sql('auth', filename)
    return dialect_converter.transpile(
        raw, source_dialect=_SOURCE_DIALECT, target_dialect=_target_dialect())


def _exe() -> SQLExecutor:
    """取「活引擎」执行器（与 app/db/user.py 同义，确保 --db 覆写下命中正确库）。"""
    return SQLExecutor()


def default_supplier() -> str:
    return get_config().DEFAULT_SUPPLIER


def list_model_ids() -> List[str]:
    """列出全部模型的 ID（cc_ObjDes.bk_obj_id，按 ID 升序）。

    用于「按场景批量授权」的辅助查询：复制输出的逗号分隔列表可直接
    传给 auth policy grant-scenario 的 --models 参数。覆盖全库模型，
    包括已暂停（bk_ispaused=1）的模型。
    """
    raw = load_sql('model', 'select_model_ids.sql')
    sql = dialect_converter.transpile(
        raw, source_dialect=_SOURCE_DIALECT, target_dialect=_target_dialect())
    rows = _exe().query_all(sql, {})
    return [r['bk_obj_id'] for r in rows]


# ---------------------------------------------------------------------------
# 用户（委托 app.db.user）
# ---------------------------------------------------------------------------
def create_user(name: str, password: str, role: int = ROLE_NORMAL,
                supplier: str = None, password_hash: str = None) -> dict:
    return _create_user(name=name, password=password, role=role,
                        supplier=supplier, password_hash=password_hash)


def get_user(name: str):
    return _get_user(name)


def list_users():
    return _list_users()


def exists_user(name: str) -> bool:
    return _exists_user(name)


def update_user_password(name: str, password: str = None, password_hash: str = None,
                         supplier: str = None) -> dict:
    return _update_user_password(name=name, password=password,
                                 password_hash=password_hash, supplier=supplier)


# ---------------------------------------------------------------------------
# 策略（cc_AuthPolicy）
# ---------------------------------------------------------------------------
def list_policies(supplier: str = None, principal: str = None,
                  res_type: str = None, obj_id: str = None,
                  action: str = None, business_id: str = None) -> List[Dict[str, Any]]:
    """列出策略（任意维度可选过滤）。

    obj_id / business_id 过滤语义：给定值时返回「该值 + 类级(NULL)」两类继承策略；
    不传则返回全部。
    """
    return _exe().query_all(_sql('select_policies.sql'), {
        'supplier': supplier,
        'principal': principal,
        'res_type': res_type,
        'obj_id': obj_id,
        'action': action,
        'business_id': business_id,
    })


def _exists_policy(supplier, principal, res_type, obj_id, action, business_id=None) -> bool:
    """精确存在性判定（不继承类级 NULL）：用于 grant 幂等。

    与 select_policies.sql 的「类级 NULL 覆盖」语义不同，这里要求
    (obj_id, business_id) 严格相等或同为 NULL，确保 (business_id='2') 与
    (business_id=NULL=全部业务) 被视为两条独立策略、互不跳过。
    """
    row = _exe().query_one(_sql('policy_exists.sql'), {
        'supplier': supplier,
        'principal': principal,
        'res_type': res_type,
        'obj_id': obj_id,
        'action': action,
        'business_id': business_id,
    })
    return row is not None


def grant_policy(supplier, principal, res_type, obj_id, action,
                 business_id: str = None, effect: str = EFFECT_ALLOW,
                 idempotent: bool = True) -> Dict[str, Any]:
    """写入一条策略（默认幂等：已存在则跳过）。

    Args:
        supplier:   供应商账户（须 == 用户 bk_supplier_account）
        principal:  用户名（== cc_UserBase.bk_user_name）
        res_type:   资源类型，模型实例固定 'modelInstance'
        obj_id:     模型 ID / 拓扑固定值；传 None 表示「该类全部模型」
        action:     create / update / delete / find / transfer
        business_id: 业务 ID（拓扑 per-biz 授权的 biz 作用域）；传 None 表示「全部业务」（类级）
        effect:     仅 'allow'
        idempotent: True 时若已存在相同 (supplier,principal,res_type,obj_id,action,business_id) 则跳过
    Returns:
        {'granted': bool, 'skipped': bool, 'policy': {...}}
    """
    action = (action or '').strip().lower()
    if action not in VALID_ACTIONS:
        raise ValueError(f'非法动作: {action}（仅 {VALID_ACTIONS}）')
    res_type = res_type or RES_TYPE_MODEL_INSTANCE
    _validate_res_type(res_type)
    effect = effect or EFFECT_ALLOW

    existing = _exists_policy(supplier, principal, res_type, obj_id, action, business_id)
    if existing:
        if idempotent:
            return {'granted': False, 'skipped': True,
                    'policy': {'supplier': supplier, 'principal': principal,
                               'res_type': res_type, 'obj_id': obj_id,
                               'business_id': business_id,
                               'action': action, 'effect': effect}}
        # 非幂等：先删后插（覆盖）
        _exe().execute(_sql('delete_policy.sql'), {
            'id': None, 'supplier': supplier, 'principal': principal,
            'res_type': res_type, 'obj_id': obj_id, 'action': action,
            'business_id': business_id,
        })

    _exe().execute(_sql('insert_policy.sql'), {
        'supplier': supplier, 'principal': principal,
        'res_type': res_type, 'obj_id': obj_id,
        'action': action, 'business_id': business_id, 'effect': effect,
    })
    return {'granted': True, 'skipped': False,
            'policy': {'supplier': supplier, 'principal': principal,
                       'res_type': res_type, 'obj_id': obj_id,
                       'business_id': business_id,
                       'action': action, 'effect': effect}}


def revoke_policy(supplier: str = None, principal: str = None,
                  res_type: str = None, obj_id: str = None, action: str = None,
                  business_id: str = None, policy_id: int = None) -> int:
    """撤销策略。

    两种用法：
      - 按主键：传 policy_id（其余可为 None）
      - 按「用户 + 资源类型 + 动作」：传 principal + res_type + action（supplier 可选）；
        obj_id 可省略（None）→ 撤销该类级（全部模型）及该动作下所有模型级策略；
        business_id 可省略（None）→ 撤销该动作下全部业务的策略（含类级 NULL 与指定业务）
    返回删除行数。
    """
    if policy_id is not None:
        return _exe().execute(_sql('delete_policy.sql'), {
            'id': policy_id, 'supplier': None, 'principal': None,
            'res_type': None, 'obj_id': None, 'action': None, 'business_id': None,
        }).rowcount
    if res_type is not None:
        _validate_res_type(res_type)
    if not principal or not action:
        raise ValueError('撤销需提供 policy_id，或 (principal + action)；obj_id 可省略（类级=全部模型）')
    return _exe().execute(_sql('delete_policy.sql'), {
        'id': None, 'supplier': supplier, 'principal': principal,
        'res_type': res_type, 'obj_id': obj_id, 'action': action,
        'business_id': business_id,
    }).rowcount


def revoke_all_for_user(principal: str, supplier: str = None) -> int:
    """撤销某用户的全部策略（删除账号前清理其策略行）。"""
    return _exe().execute(_sql('delete_policies_by_principal.sql'), {
        'principal': principal, 'supplier': supplier,
    }).rowcount


def grant_batch(items: List[Dict[str, Any]],
                idempotent: bool = True) -> Dict[str, int]:
    """批量写入策略。

    items: [{'supplier','principal','res_type','obj_id','action','effect'}, ...]
    返回统计：granted / skipped / failed。
    """
    stats = {'granted': 0, 'skipped': 0, 'failed': 0}
    for it in items:
        try:
            r = grant_policy(
                supplier=it.get('supplier', default_supplier()),
                principal=it['principal'],
                res_type=it.get('res_type', RES_TYPE_MODEL_INSTANCE),
                obj_id=it.get('obj_id'),
                action=it['action'],
                business_id=it.get('business_id'),
                effect=it.get('effect', EFFECT_ALLOW),
                idempotent=idempotent,
            )
            if r['granted']:
                stats['granted'] += 1
            else:
                stats['skipped'] += 1
        except Exception:
            stats['failed'] += 1
    return stats


# ---------------------------------------------------------------------------
# 场景化批量授权（按场景生成授权项，再走 grant_batch）
# ---------------------------------------------------------------------------
# 内置场景定义（find 读操作永远放行，无需也不写入策略，故写场景不含 find）：
#   readonly     仅查看（find），          res_type=modelInstance，作用于全部模型（obj_id=NULL）
#   readwrite    全写（create/update/delete），res_type=modelInstance，作用于全部模型（obj_id=NULL）
#   update-only  仅编辑（update），        res_type=modelInstance，作用于全部模型（obj_id=NULL）
#   model-owner  全写（create/update/delete），res_type=modelInstance，作用于单模型（需 --model）
#   topo-admin   拓扑全写（create/update/delete），res_type=biz_topology，业务无关（obj_id 固定）
#   host-transfer主机转移（transfer），    res_type=hostInstance，业务无关（obj_id 固定 'host'）
# 场景 dict 字段：actions（动作列表）、res_type（资源类型）、scope（all/model/topo/host）
SCENARIOS = {
    'readonly':     {'actions': ['find'],                  'res_type': RES_TYPE_MODEL_INSTANCE, 'scope': 'all'},
    'readwrite':    {'actions': ['create', 'update', 'delete'], 'res_type': RES_TYPE_MODEL_INSTANCE, 'scope': 'all'},
    'update-only':  {'actions': ['update'],                'res_type': RES_TYPE_MODEL_INSTANCE, 'scope': 'all'},
    'model-owner':  {'actions': ['create', 'update', 'delete'], 'res_type': RES_TYPE_MODEL_INSTANCE, 'scope': 'model'},
    'topo-admin':   {'actions': ['create', 'update', 'delete'], 'res_type': RES_TYPE_BIZ_TOPOLOGY, 'scope': 'topo'},
    'host-transfer':{'actions': ['transfer'],              'res_type': RES_TYPE_HOST_INSTANCE, 'scope': 'host'},
}


def resolve_scenario(name: str, principal: str,
                     models: Optional[List[str]] = None,
                     model: str = None,
                     supplier: str = None,
                     business_id: str = None) -> List[Dict[str, Any]]:
    """解析场景为授权项列表。

    Args:
        name:     场景名（见 SCENARIOS）
        principal:目标用户名
        models:   显式模型 ID 列表（覆盖模型场景作用域的 'all'→逐模型、'model'→多模型）
        model:    单模型 ID（scope='model' 必填；或与 models 二选一）
        supplier: 供应商账户（默认 DEFAULT_SUPPLIER）
        business_id: 业务 ID（拓扑/主机场景的 biz 作用域）；None=全部业务（类级）
    Returns:
        授权项列表，每项可直接交给 grant_batch。

    说明：
        - 模型场景（all/model）按 targets 逐个展开动作；obj_id=None 即类级（全部模型）。
        - topo/host 场景 obj_id 固定（见 app/auth/parser.py 网关产出），business_id 透传：
            business_id=None → 覆盖全部业务（类级）；business_id='2' → 仅业务 2。
          topo/host 场景忽略 --model/--models。
    """
    sup = supplier or default_supplier()
    if name not in SCENARIOS:
        raise ValueError(f'未知场景: {name}（可用: {list(SCENARIOS.keys())}）')
    scen = SCENARIOS[name]
    res_type = scen.get('res_type', RES_TYPE_MODEL_INSTANCE)
    scope = scen['scope']

    # 业务拓扑 / 主机转移：obj_id 固定，business_id 透传（忽略 --model/--models）
    if scope == 'topo':
        obj_id = RES_TYPE_BIZ_TOPOLOGY
        return [{'supplier': sup, 'principal': principal, 'res_type': res_type,
                 'obj_id': obj_id, 'action': a, 'effect': EFFECT_ALLOW,
                 'business_id': business_id}
                for a in scen['actions']]
    if scope == 'host':
        obj_id = 'host'  # 主机转移门禁 obj_id 固定为 'host'（见 app/auth/parser.py）
        return [{'supplier': sup, 'principal': principal, 'res_type': res_type,
                 'obj_id': obj_id, 'action': a, 'effect': EFFECT_ALLOW,
                 'business_id': business_id}
                for a in scen['actions']]

    # 模型作用域（all / model）
    if scope == 'model':
        targets = models or ([model] if model else [])
        if not targets:
            raise ValueError(f'场景 {name} 需要 --model 或 --models')
    else:  # all：类级（obj_id=NULL）；若给了 models 则逐模型展开
        targets = models or [None]

    items = []
    for m in targets:
        obj_id = m  # None → 类级（全部模型）
        for action in scen['actions']:
            items.append({
                'supplier': sup,
                'principal': principal,
                'res_type': res_type,
                'obj_id': obj_id,
                'action': action,
                'effect': EFFECT_ALLOW,
                'business_id': business_id,
            })
    return items


def grant_by_scenario(name: str, principal: str,
                      models: Optional[List[str]] = None,
                      model: str = None,
                      supplier: str = None,
                      business_id: str = None,
                      idempotent: bool = True) -> Dict[str, Any]:
    """按场景为用户批量授权（便捷封装）。"""
    items = resolve_scenario(name, principal, models=models, model=model,
                              supplier=supplier, business_id=business_id)
    stats = grant_batch(items, idempotent=idempotent)
    return {'scenario': name, 'principal': principal, 'items': len(items), **stats}
