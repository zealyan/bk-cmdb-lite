"""
Host Favorite 数据层（业务拓扑-主机列表「已收藏条件」）

隔离规则严格对齐上游 bk-cmdb 的 FavouriteMeta（src/common/metadata/hostcontroller.go:206）：
  - user（登录用户，对应上游 FavouriteMeta.User，服务端从 token 注入，不信任客户端）
  - bk_supplier_account（租户/供应商账户，对应上游 OwnerID，服务端注入）
  - bk_biz_id（业务，对应上游 BizID，随收藏条件携带）

所有查询/删除均强制按上述「三层」过滤，确保：
  - tom 只能看到 / 删除「tom + 本租户 + 本业务」的收藏；
  - admin 创建的收藏，tom 既看不到、也无法删除（满足「tom 无权」的 per-user 隔离语义）。

鉴权：上游此资源为 SkipType（IAM 不对其做业务 RBAC 判定），因此本模块不在
app/auth/parser.py 中覆盖对应路由——auth_filter 对其 fail-open 放行，隔离仅靠数据层。
这与上游「收藏条件无需再单独申请模型权限」的语义一致。

SQL 多方言：建表/查询/删除语句以 PostgreSQL 规范方言书写于 app/sql/favourite/*，
运行时经 app.db.dialect 转译到当前方言，切换 SQLite/PostgreSQL/MySQL 无需改代码。
"""
from datetime import datetime
import uuid
from app.db.executor import execute, query_all, insert
from app.db.sql_loader import load_sql
from app.db.dialect import dialect_converter
from app.config.settings import get_config, DialectType

TABLE = 'cc_HostFavourite'

# SQL 文件书写所用的规范方言（DialectType.POSTGRESQL = 'postgres'）
_SOURCE_DIALECT = DialectType.POSTGRESQL.value


def _target_dialect() -> str:
    """当前数据库方言（sqlglot 书写名）。"""
    return {
        'sqlite': DialectType.SQLITE.value,
        'postgresql': DialectType.POSTGRESQL.value,
        'mysql': DialectType.MYSQL.value,
    }.get(get_config().DATABASE_TYPE, DialectType.SQLITE.value)


def _sql(filename: str) -> str:
    """加载 SQL 文件并转译到当前方言（多方言核心）。"""
    raw = load_sql('favourite', filename)
    return dialect_converter.transpile(
        raw, source_dialect=_SOURCE_DIALECT, target_dialect=_target_dialect())


def init_favourite_table():
    """幂等建表（多方言 DDL，PostgreSQL 规范方言经转译执行）。"""
    execute(_sql('create_table.sql'), {})


def create_favourite(user: str, supplier: str, biz_id: int, payload: dict) -> dict:
    """创建收藏条件。user/supplier 由服务端注入（不信任客户端），biz_id 随条件携带。"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row = {
        'id': uuid.uuid4().hex,
        'bk_user': user,
        'bk_supplier_account': supplier,
        'bk_biz_id': int(biz_id or 0),
        'name': (payload.get('name') or '').strip(),
        'info': payload.get('info') or '',
        'query_params': payload.get('query_params') or '',
        'is_default': int(payload.get('is_default') or 0),
        'count': int(payload.get('count') or 0),
        'type': (payload.get('type') or 'tradition'),
        'create_time': now,
        'last_time': now,
    }
    insert(TABLE, row)
    return row


def list_favourites(user: str, supplier: str, biz_id: int) -> list:
    """查询当前用户 + 本租户 + 本业务的全部收藏（三层隔离）。"""
    return query_all(_sql('select_favourites.sql'), {
        'bk_user': user,
        'bk_supplier_account': supplier,
        'bk_biz_id': int(biz_id or 0),
    })


def delete_favourite(fav_id: int, user: str, supplier: str, biz_id: int) -> int:
    """删除收藏。WHERE 强制包含三层隔离条件，tom 即使知道 admin 的 id 也无法删除。

    Returns:
        受影响行数（0 表示不存在或无权删除）。
    """
    result = execute(_sql('delete_favourite.sql'), {
        'fav_id': fav_id,
        'bk_user': user,
        'bk_supplier_account': supplier,
        'bk_biz_id': int(biz_id or 0),
    })
    return result.rowcount if hasattr(result, 'rowcount') else 0


def update_favourite(fav_id: str, user: str, supplier: str, biz_id: int, payload: dict) -> int:
    """更新收藏条件（name / query_params / type）。WHERE 强制包含三层隔离条件，tom 无法更新 admin 的收藏。

    Returns:
        受影响行数（0 表示不存在或无权更新）。
    """
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    result = execute(_sql('update_favourite.sql'), {
        'fav_id': fav_id,
        'bk_user': user,
        'bk_supplier_account': supplier,
        'bk_biz_id': int(biz_id or 0),
        'name': (payload.get('name') or '').strip(),
        'query_params': payload.get('query_params') or '',
        'info': payload.get('info') or '',
        'type': (payload.get('type') or 'tradition'),
        'last_time': now,
    })
    return result.rowcount if hasattr(result, 'rowcount') else 0
