"""
服务分类（ServiceCategory）数据层

对齐蓝鲸 CMDB 的 ServiceCategory（src/common/metadata/process.go:1130 +
src/source_controller/coreservice/core/process/service_category.go）：
  - 业务级（bk_biz_id）两级树：bk_parent_id = 0 即一级分类，其余为二级分类；
  - bk_root_id 指向所属一级分类 id（一级分类自身 root = 自身 id）；
  - bk_supplier_account 多租户隔离（lite 默认 '0'）；
  - is_built_in 标记系统内置分类（不可改名 / 删除）。

与上游一致的语义：
  - 删除：一级分类下若存在二级分类则【禁止删除】
    （返回 CCErrServiceCategoryHasChildNode，对齐上游 CCErrCommRemoveRecordHasChildrenForbidden
     与前端「请先清空二级分类」禁用删除的提示），不再级联删除；
  - 改名：内置分类禁止修改（CCErrServiceCategoryBuiltInForbidden）；
  - 同级（bk_parent_id）下分类名称唯一（不区分大小写）。

SQL 多方言：建表/查询语句以 PostgreSQL 规范方言书写于 app/sql/service_category/*，
运行时经 app.db.dialect 转译到当前方言，切换 SQLite/PostgreSQL/MySQL 无需改代码。
连接复用 SQLAlchemy 引擎连接池（app.db.engine）。
"""
from datetime import datetime
import logging
from typing import Dict, Any, List, Optional

from app.db.executor import execute, query_all, query_one, insert, update as db_update, delete as db_delete
from app.db.sql_loader import load_sql
from app.db.dialect import dialect_converter
from app.config.settings import get_config, DialectType
from app.utils.tools import generate_id
from app.utils.exceptions import APIException, CCErrorCode

TABLE = 'cc_ServiceCategory'

# SQL 文件书写所用的规范方言（DialectType.POSTGRESQL = 'postgres'）
_SOURCE_DIALECT = DialectType.POSTGRESQL.value

# 分类名称长度上限（与原项目 ServiceCategoryMaxLength 一致）
NAME_MAX_LENGTH = 64

# 内置默认分类名称（对齐上游 common.DefaultServiceCategoryName，definitions.go:1583）
DEFAULT_CATEGORY_NAME = 'Default'

logger_info = logging.getLogger(__name__).info


def _target_dialect() -> str:
    """当前数据库方言（sqlglot 书写名）。"""
    return {
        'sqlite': DialectType.SQLITE.value,
        'postgresql': DialectType.POSTGRESQL.value,
        'mysql': DialectType.MYSQL.value,
    }.get(get_config().DATABASE_TYPE, DialectType.SQLITE.value)


def _sql(filename: str) -> str:
    """加载 SQL 文件并转译到当前方言（多方言核心，对齐 favourite 范式）。

    注意：sql_loader.load 要求 filename 含 .sql 后缀，这里统一兜底补上，
    调用处只需传逻辑名（select_list / count_name_exists ...）。
    """
    if not filename.endswith('.sql'):
        filename = filename + '.sql'
    raw = load_sql('service_category', filename)
    return dialect_converter.transpile(
        raw, source_dialect=_SOURCE_DIALECT, target_dialect=_target_dialect())


def init_service_category_table():
    """幂等建表（多方言 DDL，PostgreSQL 规范方言经转译执行）。"""
    execute(_sql('create_table.sql'), {})


def _now() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _normalize_supplier(supplier: Optional[str]) -> str:
    return (supplier or '0').strip() or '0'


def _query_ids(sql: str, params: Dict[str, Any]) -> List[int]:
    """执行查询并返回 id 列（int 列表）。"""
    rows = query_all(sql, params)
    return [int(r['id']) for r in rows if r.get('id') is not None]


def ensure_default_categories(supplier: str = '0') -> Optional[int]:
    """幂等初始化两级内置 Default 服务分类，返回二级分类 id。

    完全对齐上游 x19.05.16.01/add_default_category.go 的 addDefaultCategory：
      - 一级：name='Default', bk_parent_id=0, bk_root_id=自身 id,
              is_built_in=1, bk_supplier_account='0', bk_biz_id=0（全局，非业务私有）；
      - 二级：name='Default', bk_parent_id=一级 id, bk_root_id=一级 root_id，
              同样 is_built_in=1 / 全局；
      - 返回【二级分类 id】作为模块默认所属服务分类（上游同语义）。

    幂等：已存在则直接复用，不重复插入、不改名。
    """
    init_service_category_table()
    supplier = _normalize_supplier(supplier)
    now = _now()

    # 一级 Default
    first_ids = _query_ids(
        'SELECT id FROM cc_ServiceCategory '
        'WHERE bk_supplier_account = :s AND bk_biz_id = 0 '
        '  AND bk_parent_id = 0 AND name = :name',
        {'s': supplier, 'name': DEFAULT_CATEGORY_NAME})
    if first_ids:
        first_id = first_ids[0]
    else:
        first_id = generate_id(scope='service_category')
        insert(TABLE, {
            'id': first_id,
            'bk_biz_id': 0,
            'name': DEFAULT_CATEGORY_NAME,
            'bk_root_id': first_id,
            'bk_parent_id': 0,
            'bk_supplier_account': supplier,
            'is_built_in': 1,
            'create_time': now,
            'last_time': now,
        })
        logger_info(f'初始化内置一级服务分类 {DEFAULT_CATEGORY_NAME}(id={first_id})')

    # 二级 Default（父级为一级 Default）
    second_ids = _query_ids(
        'SELECT id FROM cc_ServiceCategory '
        'WHERE bk_supplier_account = :s AND bk_biz_id = 0 '
        '  AND bk_parent_id = :pid AND name = :name',
        {'s': supplier, 'pid': first_id, 'name': DEFAULT_CATEGORY_NAME})
    if second_ids:
        return second_ids[0]

    second_id = generate_id(scope='service_category')
    insert(TABLE, {
        'id': second_id,
        'bk_biz_id': 0,
        'name': DEFAULT_CATEGORY_NAME,
        'bk_root_id': first_id,
        'bk_parent_id': first_id,
        'bk_supplier_account': supplier,
        'is_built_in': 1,
        'create_time': now,
        'last_time': now,
    })
    logger_info(f'初始化内置二级服务分类 {DEFAULT_CATEGORY_NAME}(id={second_id})')
    return second_id


def get_default_category_id(supplier: str = '0') -> Optional[int]:
    """获取内置默认服务分类（二级）id；不存在返回 None。

    对齐上游 coreservice GetDefaultServiceCategory
    （/find/process/default_service_category）：返回 addDefaultCategory 落库的
    二级分类 id，作为新建模块「所属服务分类」的默认值。
    """
    supplier = _normalize_supplier(supplier)
    # 优先按「父级为内置一级 Default」精确定位二级分类
    second_ids = _query_ids(
        'SELECT c.id FROM cc_ServiceCategory c '
        'WHERE c.bk_supplier_account = :s AND c.bk_biz_id = 0 AND c.is_built_in = 1 '
        '  AND c.bk_parent_id <> 0 '
        '  AND c.name = :name',
        {'s': supplier, 'name': DEFAULT_CATEGORY_NAME})
    if second_ids:
        return second_ids[0]
    # 兜底：任意内置二级分类（非一级，bk_parent_id != 0）
    fallback = _query_ids(
        'SELECT id FROM cc_ServiceCategory '
        'WHERE bk_supplier_account = :s AND bk_biz_id = 0 AND is_built_in = 1 '
        '  AND bk_parent_id <> 0 '
        'ORDER BY id ASC',
        {'s': supplier})
    return fallback[0] if fallback else None


def _count(sql_key: str, params: Dict[str, Any]) -> int:
    """读取 COUNT(*) AS cnt 查询结果。"""
    row = query_one(_sql(sql_key), params)
    return int(row['cnt']) if row and row.get('cnt') is not None else 0


def list_categories(biz_id: int, supplier: str = '0') -> List[Dict[str, Any]]:
    """查询某业务下的全部服务分类（扁平列表，按 id 升序）。

    与上游 findmany/process/service_category 一致：返回扁平结构，
    前端按 bk_parent_id / bk_root_id 组装两级树；额外附带 usage_amount
    （该分类被模块引用的数量，对齐原项目 usage_amount 字段），供前端
    「分类被模块占用则禁用删除」逻辑使用。
    """
    raw = query_all(
        _sql('select_list.sql'),
        {'bk_biz_id': int(biz_id or 0), 'bk_supplier_account': _normalize_supplier(supplier)}
    )
    usage = _category_usage_map(biz_id, supplier)
    result = []
    for row in raw:
        enriched = dict(row)
        enriched['usage_amount'] = usage.get(int(row['id']), 0)
        result.append(_serialize(enriched))
    return result


def _category_usage_map(biz_id: int, supplier: str = '0') -> Dict[int, int]:
    """统计某业务下各服务分类被模块（cc_ModuleBase.service_category_id）引用的数量。

    返回 {分类 id: 引用计数}，对齐原项目 usage_amount 字段，供前端
    「分类被模块占用则禁用删除」使用。未被引用的分类不在映射中（默认 0）。
    """
    rows = query_all(
        _sql('count_module_usage.sql'),
        {
            'bk_biz_id': int(biz_id or 0),
            'bk_supplier_account': _normalize_supplier(supplier),
        }
    )
    return {int(r['service_category_id']): int(r['cnt']) for r in rows}


def _get_category(cat_id: int, supplier: str = '0') -> Optional[Dict[str, Any]]:
    return query_one(
        _sql('select_one.sql'),
        {'cat_id': int(cat_id), 'bk_supplier_account': _normalize_supplier(supplier)}
    )


def _name_exists(biz_id: int, parent_id: int, name: str, supplier: str,
                 exclude_id: Optional[int] = None) -> bool:
    """同一父级（bk_parent_id）下分类名称唯一（不区分大小写）。"""
    params = {
        'bk_biz_id': int(biz_id),
        'bk_parent_id': int(parent_id),
        'bk_supplier_account': _normalize_supplier(supplier),
        'name': (name or '').strip(),
        'exclude_id': int(exclude_id) if exclude_id is not None else 0,
    }
    return _count('count_name_exists', params) > 0


def create_category(biz_id: int, name: str, parent_id: int = 0,
                    supplier: str = '0') -> Dict[str, Any]:
    """创建服务分类。

    - parent_id = 0 → 一级分类，bk_root_id = 自身 id；
    - parent_id ≠ 0 → 二级分类，bk_root_id 继承父级 root_id，且父级须为本业务同租户的一级分类。
    同名唯一性（同一父级下）校验不通过时抛 APIException。
    """
    biz_id = int(biz_id or 0)
    parent_id = int(parent_id or 0)
    supplier = _normalize_supplier(supplier)
    name = (name or '').strip()

    if not name:
        raise APIException('分类名称不能为空', error_code=CCErrorCode.CCErrCommParamsInvalid)
    if len(name) > NAME_MAX_LENGTH:
        raise APIException(f'分类名称长度不能超过 {NAME_MAX_LENGTH} 个字符', error_code=CCErrorCode.CCErrCommParamsInvalid)

    root_id = 0
    if parent_id != 0:
        parent = _get_category(parent_id, supplier)
        if not parent:
            raise APIException('父级分类不存在', error_code=CCErrorCode.CCErrCommParamsInvalid)
        if int(parent['bk_biz_id']) != biz_id:
            raise APIException('父级分类不属于当前业务', error_code=CCErrorCode.CCErrCommParamsInvalid)
        if int(parent['bk_parent_id']) != 0:
            raise APIException('二级分类下不能再创建子分类', error_code=CCErrorCode.CCErrCommParamsInvalid)
        root_id = int(parent['bk_root_id'])

    if _name_exists(biz_id, parent_id, name, supplier):
        raise APIException(f'同级下已存在分类「{name}」', error_code=CCErrorCode.CCErrCommParamsInvalid)

    cat_id = generate_id(scope='service_category')
    now = _now()
    if root_id == 0:
        root_id = cat_id

    row = {
        'id': cat_id,
        'bk_biz_id': biz_id,
        'name': name,
        'bk_root_id': root_id,
        'bk_parent_id': parent_id,
        'bk_supplier_account': supplier,
        'is_built_in': 0,
        'create_time': now,
        'last_time': now,
    }
    insert(TABLE, row)
    return _serialize(row)


def update_category(cat_id: int, name: str, supplier: str = '0') -> Dict[str, Any]:
    """重命名服务分类（内置分类不可改；同名唯一性校验）。"""
    supplier = _normalize_supplier(supplier)
    cat = _get_category(cat_id, supplier)
    if not cat:
        raise APIException('分类不存在', error_code=CCErrorCode.CCErrCommNotFound)
    if int(cat['is_built_in']) == 1:
        raise APIException('内置分类不可修改', error_code=CCErrorCode.CCErrServiceCategoryBuiltInForbidden)

    name = (name or '').strip()
    if not name:
        raise APIException('分类名称不能为空', error_code=CCErrorCode.CCErrCommParamsInvalid)
    if len(name) > NAME_MAX_LENGTH:
        raise APIException(f'分类名称长度不能超过 {NAME_MAX_LENGTH} 个字符', error_code=CCErrorCode.CCErrCommParamsInvalid)

    if _name_exists(int(cat['bk_biz_id']), int(cat['bk_parent_id']), name, supplier, exclude_id=cat_id):
        raise APIException(f'同级下已存在分类「{name}」', error_code=CCErrorCode.CCErrCommParamsInvalid)

    db_update(TABLE,
              {'name': name, 'last_time': _now()},
              {'id': cat_id, 'bk_supplier_account': supplier})
    return _serialize({**cat, 'name': name, 'last_time': _now()})


def delete_category(cat_id: int, supplier: str = '0') -> int:
    """删除服务分类。

    与上游一致：
      - 内置分类不可删除（CCErrServiceCategoryBuiltInForbidden）；
      - 一级分类下存在二级分类时【禁止删除】（CCErrServiceCategoryHasChildNode），
        由调用方（前端）先清空二级分类；不再级联删除。
    返回被删除的分类总数（含子分类）。
    """
    supplier = _normalize_supplier(supplier)
    cat = _get_category(cat_id, supplier)
    if not cat:
        raise APIException('分类不存在', error_code=CCErrorCode.CCErrCommNotFound)
    if int(cat['is_built_in']) == 1:
        raise APIException('内置分类不可删除', error_code=CCErrorCode.CCErrServiceCategoryBuiltInForbidden)

    # 有子分类则禁止删除（对齐上游 CCErrCommRemoveRecordHasChildrenForbidden + 前端提示）
    children_count = _count('count_children', {
        'parent_id': cat_id, 'bk_supplier_account': supplier})
    if children_count > 0:
        raise APIException(
            f'该分类下存在 {children_count} 个子分类，请先清空二级分类',
            error_code=CCErrorCode.CCErrServiceCategoryHasChildNode)

    affected = db_delete(TABLE, {'id': cat_id, 'bk_supplier_account': supplier})
    return affected


def get_category_with_path(cat_id: int, supplier: str = '0') -> Dict[str, Any]:
    """按 id 查询单个分类，并解析其两级路径（一级 / 二级名称）。

    与上游 node-extra-info-service-template 的展示一致：模块节点展示
    「服务分类：一级分类 / 二级分类」。二级分类（bk_parent_id != 0）取
    其根（bk_root_id）作为一级；一级分类自身即为一级，二级为空。
    """
    supplier = _normalize_supplier(supplier)
    cat = _get_category(cat_id, supplier)
    if not cat:
        raise APIException('分类不存在', error_code=CCErrorCode.CCErrCommNotFound)
    result = _serialize(cat)
    if int(cat['bk_parent_id']) == 0:
        # 一级分类：本身即一级，无二级
        result['first_level'] = {'id': int(cat['id']), 'name': cat['name']}
        result['second_level'] = None
    else:
        # 二级分类：一级取其根（bk_root_id）
        root = _get_category(int(cat['bk_root_id']), supplier)
        result['first_level'] = (
            {'id': int(root['id']), 'name': root['name']} if root else None)
        result['second_level'] = {'id': int(cat['id']), 'name': cat['name']}
    return result


def _serialize(row: Dict[str, Any]) -> Dict[str, Any]:
    """规整字段类型，避免 Decimal / int 混用导致前端类型不一致。"""
    return {
        'id': int(row['id']),
        'bk_biz_id': int(row['bk_biz_id']),
        'name': row['name'],
        'bk_root_id': int(row['bk_root_id']),
        'bk_parent_id': int(row['bk_parent_id']),
        'bk_supplier_account': row['bk_supplier_account'],
        'is_built_in': int(row['is_built_in']),
        'usage_amount': int(row.get('usage_amount') or 0),
    }
