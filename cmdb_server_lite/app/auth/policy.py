"""
内置 RBAC 策略存储（多方言，复用现有 db 引擎）

表 cc_AuthPolicy：supplier / principal / res_type / obj_id / action / effect
判定规则（对齐上游 ac/extensions 语义）：
  - supplier 隔离：策略必须匹配当前用户供应商账户（id0/id1 互不可见）
  - 管理员全权：principal == 配置 ADMIN_USER → 所有资源 allow
  - 创建者自动授权：实例写入时打 creator，并对该模型写 allow(update/delete)
  - 读可跳过：action==find 默认 allow（SkipReadAuthorization）

注意：obj_id 是【模型级】作用域（如 bk_slb，或 NULL=该类全部），
与实例 ID（bk_inst_id）正交；实例级判定下沉到 owner 维度（见 manager.check_instances）。
"""

from app.db.executor import query_one, insert, execute
from app.db.sql_loader import load_sql
from app.db.dialect import dialect_converter
from app.config.settings import get_config, DialectType

TABLE = 'cc_AuthPolicy'

# SQL 文件书写所用的规范方言（DialectType.POSTGRESQL = 'postgres'）
_SOURCE_DIALECT = DialectType.POSTGRESQL.value


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


def init_policy_table():
    """幂等建表（多方言 DDL，PostgreSQL 规范方言经转译执行）。

    旧库兼容：CREATE TABLE IF NOT EXISTS 不会为已存在的表补列，故若 business_id 列
    缺失则按需 ALTER（对齐上游 per-biz 授权所需的独立列；重复执行会因 duplicate column 忽略）。
    """
    execute(_sql('create_policy_table.sql'), {})
    try:
        execute("ALTER TABLE cc_AuthPolicy ADD COLUMN business_id VARCHAR(64)", {})
    except Exception:
        pass


def query_allow(supplier, principal, res_type, obj_id, actions, business_id=None):
    """模型级策略命中：该用户对【整个模型/拓扑资源】（obj_id 或 NULL=全部）在
    【指定业务 business_id，或 NULL=全部业务】是否有 actions 中任一 allow。

    多方言：SQL 骨架取自 app/sql/auth/policy_query_allow.sql（PostgreSQL 规范方言），
    经 _sql() 转译到当前方言；动态 IN 列表（__ACTIONS__ 哨兵）由 Python 组装，
    占位符 :a_0,:a_1… 各方言通用，不参与转译。
    business_id 语义（对齐上游 bizTopology 以 business 为父级作用域）：
      - 请求带 business_id=B → 命中 business_id=B 的专属策略，或 business_id=NULL 的类级策略
      - 请求 business_id=None  → 仅命中 business_id=NULL 的策略（模型实例等无 biz 维度的资源）
    """
    if isinstance(actions, str):
        actions = [actions]
    placeholders = ','.join([f':a_{i}' for i in range(len(actions))])
    params = {f'a_{i}': a for i, a in enumerate(actions)}
    params.update({'supplier': supplier, 'principal': principal,
                   'res_type': res_type, 'obj_id': obj_id,
                   'business_id': business_id})
    sql = _sql('policy_query_allow.sql').replace('__ACTIONS__', placeholders)
    row = query_one(sql, params)
    return bool(row and row.get('effect') == 'allow')


def grant_creator(model_id, supplier, principal,
                   actions=('update', 'delete', 'find')):
    """创建者自动授权（对齐上游 RegisterResourceCreatorAction）。

    动作集对齐上游 ac/iam/initial_resource_creator_actions.go：创建者获得
    Edit / Delete / Find，【不含 Create】——资源已由其创建，无需再授创建权。
    批量动作亦不再授予：上游 parser 已将批量端点逐实例展开为单动作资源
    （见 auth/parser.py），故 update/delete 即可覆盖批量场景。
    """
    for action in actions:
        exists = query_one(
            _sql('policy_grant_creator_check.sql'),
            {'s': supplier, 'p': principal, 'o': model_id, 'a': action})
        if not exists:
            insert(TABLE, {
                'supplier': supplier, 'principal': principal,
                'res_type': 'modelInstance', 'obj_id': model_id,
                'action': action, 'effect': 'allow'})


def add_policy(supplier, principal, res_type, obj_id, action, effect='allow'):
    """通用策略写入（运维/种子数据用）"""
    insert(TABLE, {
        'supplier': supplier, 'principal': principal,
        'res_type': res_type, 'obj_id': obj_id,
        'action': action, 'effect': effect})
