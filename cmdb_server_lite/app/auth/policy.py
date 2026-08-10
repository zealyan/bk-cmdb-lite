"""
内置 RBAC 策略存储（SQLite，复用现有 db）

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
from app.config.settings import get_config

TABLE = 'cc_AuthPolicy'


def init_policy_table():
    """幂等建表"""
    execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier  TEXT NOT NULL,
            principal TEXT NOT NULL,
            res_type  TEXT NOT NULL,
            obj_id    TEXT,
            action    TEXT NOT NULL,
            effect    TEXT NOT NULL DEFAULT 'allow'
        )
    """)


def query_allow(supplier, principal, res_type, obj_id, actions):
    """模型级策略命中：该用户对【整个模型】（obj_id 或 NULL=全部）是否有 actions 中任一 allow。"""
    if isinstance(actions, str):
        actions = [actions]
    placeholders = ','.join([f':a_{i}' for i in range(len(actions))])
    params = {f'a_{i}': a for i, a in enumerate(actions)}
    params.update({'supplier': supplier, 'principal': principal,
                   'res_type': res_type, 'obj_id': obj_id})
    row = query_one(f"""
        SELECT effect FROM {TABLE}
        WHERE supplier = :supplier AND principal = :principal
          AND res_type = :res_type
          AND (obj_id = :obj_id OR obj_id IS NULL)
          AND action IN ({placeholders})
        LIMIT 1
    """, params)
    return bool(row and row.get('effect') == 'allow')


def grant_creator(model_id, supplier, principal,
                   actions=('create', 'update', 'updateMany', 'delete', 'deleteMany')):
    """创建者自动授权（对齐上游 RegisterResourceCreatorAction）。

    实例创建成功后对该模型写 allow（含批量动作），使创建者凭【模型级策略】即可管理
    自身实例，亦配合实例级 owner 判定（manager.check_instances 的 c 分支）形成双重保险。
    批量动作（updateMany/deleteMany）一并授权，避免被粗粒度网关层误拒（见 §4.4）。
    """
    for action in actions:
        exists = query_one(
            f"""SELECT id FROM {TABLE}
                WHERE supplier=:s AND principal=:p
                  AND res_type='modelInstance' AND obj_id=:o AND action=:a""",
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
