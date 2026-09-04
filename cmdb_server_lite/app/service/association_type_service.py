"""
关联类型（AssociationKind / cc_AsstDes）数据层

对齐蓝鲸 CMDB 原项目：
  - 数据结构：src/common/metadata/association.go:402-421 AssociationKind
        id / bk_asst_id / bk_asst_name / bk_supplier_account
        src_des（源→目标描述）/ dest_des（目标→源描述）
        direction（方向）/ ispre（是否预置）
  - CRUD 逻辑：src/source_controller/coreservice/core/association/kind.go
               src/source_controller/coreservice/core/association/kind_crud.go
  - 删除保护：src/scene_server/topo_server/logics/model/association.go:88-137

方向 direction 的值域严格对齐上游 metadata.AssociationDirection
（none / src_to_dest / dest_to_src / bidirectional），常量定义见
app/definitions.py（含上游常量命名与取值错位的说明）。

与上游一致的校验语义：
  - 创建：bk_asst_id 全局唯一（isExists → CCErrCommDuplicateItem）；
          bk_asst_id 长度 ≤ 128 且匹配 ^[a-zA-Z]\\w*$（kind_crud.isValid，
          对应上游 AttributeIDMaxLength / FieldTypeStrictCharRegexp）；
  - 更新：仅 bk_asst_name / src_des / dest_des / direction 四个字段可改
          （对齐上游 topo 层 UpdateAssociationType 的固定字段集）；
          id / bk_asst_id / ispre 不可改（对齐 SetAssociationKind 的 Remove）。
          注意上游【允许】修改预置类型（ispre=true）的这四个字段，仅删除受限，
          lite 保持同一语义，不额外加严。
  - 删除：预置类型（ispre=true）禁止删除（CCErrorTopoDeletePredefinedAssociationKind）；
          已被模型关联（cc_ObjAsst）引用的类型禁止删除
          （CCErrorTopoAssociationKindHasBeenUsed）。

lite 相对上游的增强（有意为之，非偏离）：
  - direction 做严格值域校验。上游 kind_crud.isValid 只校验 bk_asst_id，
    direction 可写入任意字符串（其单测甚至用 Direction="test" 通过），
    会产生前端无法识别的脏方向数据 —— lite 在入口拒绝非法值。
  - 更新语义为「未传字段保留原值」（上游是四字段全量覆盖，未传即被写空）。

SQL 多方言：查询语句以 PostgreSQL 规范方言书写于 app/sql/association/*，
运行时经 app.db.dialect 转译到当前方言；写操作走 executor 表级 API
（insert / update / delete），同样经 adapt_sql 适配方言。
连接复用 SQLAlchemy 引擎连接池（app.db.engine）。
"""
from datetime import datetime
import logging
import re
from typing import Any, Dict, List, Optional

from app.config.settings import DialectType, get_config
from app.db.dialect import dialect_converter
from app.db.executor import (
    delete as db_delete,
    insert,
    query_all,
    query_one,
    update as db_update,
)
from app.db.sql_loader import load_sql
from app.definitions import (
    ASST_DIRECTION_LABELS,
    DEFAULT_ASST_DIRECTION,
    VALID_ASST_DIRECTIONS,
    normalize_asst_direction,
)
from app.utils.exceptions import APIException, CCErrorCode
from app.utils.tools import generate_id

TABLE = 'cc_AsstDes'

# SQL 文件书写所用的规范方言（DialectType.POSTGRESQL = 'postgres'）
_SOURCE_DIALECT = DialectType.POSTGRESQL.value

# bk_asst_id 长度上限与字符规则，对齐上游 kind_crud.isValid：
#   common.AttributeIDMaxLength = 128（definitions.go:1555）
#   common.FieldTypeStrictCharRegexp = `^[a-zA-Z]\w*$`（definitions.go:1067）
ASST_ID_MAX_LENGTH = 128
ASST_ID_PATTERN = re.compile(r'^[a-zA-Z]\w*$')

# 显示名长度上限，对齐上游 AttributeNameMaxLength（definitions.go:1557）
ASST_NAME_MAX_LENGTH = 128

# 关联描述（src_des / dest_des）长度上限。上游未单独设限，lite 取与显示名同量级，
# 避免超长文案破坏 UI 布局。
ASST_DES_MAX_LENGTH = 128

# 更新时允许修改的字段白名单（对齐上游 topo 层 UpdateAssociationType 的固定字段集）
UPDATABLE_FIELDS = ('bk_asst_name', 'src_des', 'dest_des', 'direction')

# 默认图标（lite 扩展字段，上游 cc_AsstDes 无此列）
DEFAULT_ASST_ICON = 'icon-cc-default'

logger = logging.getLogger(__name__)


def _target_dialect() -> str:
    """当前数据库方言（sqlglot 书写名）。"""
    return {
        'sqlite': DialectType.SQLITE.value,
        'postgresql': DialectType.POSTGRESQL.value,
        'mysql': DialectType.MYSQL.value,
    }.get(get_config().DATABASE_TYPE, DialectType.SQLITE.value)


def _sql(filename: str) -> str:
    """加载 SQL 文件并转译到当前方言（多方言核心，对齐 service_category 范式）。"""
    if not filename.endswith('.sql'):
        filename = filename + '.sql'
    raw = load_sql('association', filename)
    return dialect_converter.transpile(
        raw, source_dialect=_SOURCE_DIALECT, target_dialect=_target_dialect())


def _now() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _normalize_supplier(supplier: Optional[str]) -> str:
    return (supplier or '0').strip() or '0'


def _serialize(row: Dict[str, Any]) -> Dict[str, Any]:
    """规整单条关联类型的出参类型。

    - ispre 统一为 bool（SQLite 存 0/1、PostgreSQL 存 true/false，前端按布尔用）；
    - id 统一为 int；
    - src_des / dest_des 为 NULL 时回退为空串（前端直接拼接展示，避免 undefined）；
    - direction 兜底归一（防御历史脏数据绕过迁移直接进接口）；
    - 附带 direction_label 便于 CLI / UI 直接展示中文方向名。
    """
    if not row:
        return {}
    data = dict(row)
    if data.get('id') is not None:
        data['id'] = int(data['id'])
    data['ispre'] = bool(data.get('ispre'))
    data['src_des'] = data.get('src_des') or ''
    data['dest_des'] = data.get('dest_des') or ''
    data['direction'] = normalize_asst_direction(data.get('direction'))
    data['direction_label'] = ASST_DIRECTION_LABELS.get(data['direction'], data['direction'])
    return data


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

def validate_direction(direction: Any, allow_empty: bool = False) -> Optional[str]:
    """严格校验方向取值，返回合法方向。

    :param direction: 待校验值
    :param allow_empty: 为 True 时，空值返回 None（表示"本次不修改该字段"）；
                        为 False 时，空值回退为 DEFAULT_ASST_DIRECTION
    :raises APIException: 取值不在上游合法值域内
    """
    if direction is None or str(direction).strip() == '':
        return None if allow_empty else DEFAULT_ASST_DIRECTION

    value = str(direction).strip()
    if value not in VALID_ASST_DIRECTIONS:
        raise APIException(
            f"方向 direction 取值非法: {value!r}，合法取值为 "
            f"{' / '.join(VALID_ASST_DIRECTIONS)}"
            f"（分别表示：{' / '.join(ASST_DIRECTION_LABELS[d] for d in VALID_ASST_DIRECTIONS)}）",
            error_code=CCErrorCode.CCErrCommParamsInvalid)
    return value


def _validate_asst_id(asst_id: Any) -> str:
    """校验 bk_asst_id（对齐上游 kind_crud.isValid）。"""
    value = (asst_id or '')
    value = str(value).strip()
    if not value:
        raise APIException('关联类型 ID（bk_asst_id）不能为空',
                           error_code=CCErrorCode.CCErrCommParamsInvalid)
    if len(value) > ASST_ID_MAX_LENGTH:
        raise APIException(
            f'关联类型 ID 长度不能超过 {ASST_ID_MAX_LENGTH} 个字符',
            error_code=CCErrorCode.CCErrCommParamsInvalid)
    if not ASST_ID_PATTERN.match(value):
        raise APIException(
            f'关联类型 ID 不合法: {value!r}，需以字母开头，仅含字母、数字、下划线',
            error_code=CCErrorCode.CCErrCommParamsInvalid)
    return value


def _validate_name(name: Any, field: str = 'bk_asst_name',
                   label: str = '关联类型名称', required: bool = True,
                   max_length: int = ASST_NAME_MAX_LENGTH) -> Optional[str]:
    """校验显示名 / 描述类文本字段。"""
    if name is None:
        if required:
            raise APIException(f'{label}（{field}）不能为空',
                               error_code=CCErrorCode.CCErrCommParamsInvalid)
        return None
    value = str(name).strip()
    if not value:
        if required:
            raise APIException(f'{label}（{field}）不能为空',
                               error_code=CCErrorCode.CCErrCommParamsInvalid)
        return ''
    if len(value) > max_length:
        raise APIException(f'{label}长度不能超过 {max_length} 个字符',
                           error_code=CCErrorCode.CCErrCommParamsInvalid)
    return value


# ---------------------------------------------------------------------------
# 查询
# ---------------------------------------------------------------------------

def list_association_types(supplier: str = '0') -> List[Dict[str, Any]]:
    """关联类型列表（含方向与双向描述字段）。"""
    supplier = _normalize_supplier(supplier)
    rows = query_all(_sql('select_association_types'),
                     {'bk_supplier_account': supplier})
    return [_serialize(r) for r in rows]


def get_association_type(kind_id: int, supplier: str = '0') -> Optional[Dict[str, Any]]:
    """按自增 id 查询单个关联类型（对齐上游按 {id} 定位的更新/删除接口）。"""
    supplier = _normalize_supplier(supplier)
    try:
        kind_id = int(kind_id)
    except (TypeError, ValueError):
        return None
    row = query_one(_sql('select_association_type_by_id'),
                    {'id': kind_id, 'bk_supplier_account': supplier})
    return _serialize(row) if row else None


def get_association_type_by_asst_id(asst_id: str,
                                    supplier: str = '0') -> Optional[Dict[str, Any]]:
    """按 bk_asst_id 查询单个关联类型（用于唯一性判重）。"""
    supplier = _normalize_supplier(supplier)
    row = query_one(_sql('select_association_type_by_asst_id'),
                    {'bk_asst_id': asst_id, 'bk_supplier_account': supplier})
    return _serialize(row) if row else None


def count_object_associations(asst_id: str, supplier: str = '0') -> int:
    """统计该关联类型被多少个模型关联（cc_ObjAsst）引用。"""
    supplier = _normalize_supplier(supplier)
    row = query_one(_sql('count_object_associations_by_kind'),
                    {'bk_asst_id': asst_id, 'bk_supplier_account': supplier})
    return int((row or {}).get('cnt') or 0)


# ---------------------------------------------------------------------------
# 写操作
# ---------------------------------------------------------------------------

def create_association_type(data: Dict[str, Any], supplier: str = '0',
                            operator: str = 'admin') -> Dict[str, Any]:
    """创建关联类型。

    入参（对齐上游 metadata.AssociationKind 的 json tag）：
        bk_asst_id    必填，关联类型唯一标识（^[a-zA-Z]\\w*$，≤128）
        bk_asst_name  必填，显示名
        src_des       选填，源→目标 的关系描述（如"访问"）
        dest_des      选填，目标→源 的关系描述（如"被访问"）
        direction     选填，方向，缺省 src_to_dest；
                      合法值 none / src_to_dest / dest_to_src / bidirectional
        bk_asst_icon  选填，图标（lite 扩展字段）

    ispre 恒为 False —— 预置标记只能由 migrate 种子写入，不开放给接口，
    避免用户自建类型伪装成不可删除的预置类型。
    """
    data = data or {}
    supplier = _normalize_supplier(supplier)

    asst_id = _validate_asst_id(data.get('bk_asst_id'))
    asst_name = _validate_name(data.get('bk_asst_name'))
    src_des = _validate_name(data.get('src_des'), 'src_des', '源到目标描述',
                             required=False, max_length=ASST_DES_MAX_LENGTH) or ''
    dest_des = _validate_name(data.get('dest_des'), 'dest_des', '目标到源描述',
                              required=False, max_length=ASST_DES_MAX_LENGTH) or ''
    direction = validate_direction(data.get('direction'))

    if get_association_type_by_asst_id(asst_id, supplier):
        raise APIException(f'关联类型「{asst_id}」已存在',
                           error_code=CCErrorCode.CCErrCommDuplicateItem)

    now = _now()
    row = {
        'id': generate_id(scope='association_type'),
        'bk_asst_id': asst_id,
        'bk_asst_name': asst_name,
        'bk_asst_icon': (data.get('bk_asst_icon') or DEFAULT_ASST_ICON),
        'src_des': src_des,
        'dest_des': dest_des,
        'direction': direction,
        'ispre': False,
        'creator': operator,
        'modifier': operator,
        'create_time': now,
        'last_time': now,
        'bk_supplier_account': supplier,
    }
    insert(TABLE, row)
    logger.info('创建关联类型 %s(id=%s) direction=%s src_des=%r dest_des=%r',
                asst_id, row['id'], direction, src_des, dest_des)
    return _serialize(row)


def update_association_type(kind_id: int, data: Dict[str, Any], supplier: str = '0',
                            operator: str = 'admin') -> Dict[str, Any]:
    """更新关联类型的名称 / 双向描述 / 方向。

    仅 UPDATABLE_FIELDS 内的字段可改（对齐上游 topo 层 UpdateAssociationType）；
    id / bk_asst_id / ispre 一律忽略，传了也不生效。
    未传的字段保留原值（上游是全量覆盖为空，lite 取更友好的语义）。
    """
    data = data or {}
    supplier = _normalize_supplier(supplier)

    origin = get_association_type(kind_id, supplier)
    if not origin:
        raise APIException(f'关联类型不存在（id={kind_id}）',
                           error_code=CCErrorCode.CCErrCommNotFound)

    changes: Dict[str, Any] = {}

    if 'bk_asst_name' in data:
        changes['bk_asst_name'] = _validate_name(data.get('bk_asst_name'))
    if 'src_des' in data:
        changes['src_des'] = _validate_name(
            data.get('src_des'), 'src_des', '源到目标描述',
            required=False, max_length=ASST_DES_MAX_LENGTH) or ''
    if 'dest_des' in data:
        changes['dest_des'] = _validate_name(
            data.get('dest_des'), 'dest_des', '目标到源描述',
            required=False, max_length=ASST_DES_MAX_LENGTH) or ''
    if 'direction' in data:
        direction = validate_direction(data.get('direction'), allow_empty=True)
        if direction is not None:
            changes['direction'] = direction

    if not changes:
        raise APIException(
            f"没有可更新的字段，可更新字段为：{' / '.join(UPDATABLE_FIELDS)}",
            error_code=CCErrorCode.CCErrCommParamsInvalid)

    changes['modifier'] = operator
    changes['last_time'] = _now()
    db_update(TABLE, changes,
              {'id': int(kind_id), 'bk_supplier_account': supplier})
    logger.info('更新关联类型 %s(id=%s) 变更=%s',
                origin['bk_asst_id'], kind_id,
                {k: v for k, v in changes.items() if k in UPDATABLE_FIELDS})
    return _serialize({**origin, **changes})


def delete_association_type(kind_id: int, supplier: str = '0') -> Dict[str, Any]:
    """删除关联类型。

    与上游 logics/model/association.go:88-137 双重保护一致：
      1. 预置类型（ispre=true）禁止删除；
      2. 已被模型关联（cc_ObjAsst）引用的类型禁止删除。
    返回被删除类型的摘要（供调用方回显 / 审计）。
    """
    supplier = _normalize_supplier(supplier)
    origin = get_association_type(kind_id, supplier)
    if not origin:
        raise APIException(f'关联类型不存在（id={kind_id}）',
                           error_code=CCErrorCode.CCErrCommNotFound)

    if origin['ispre']:
        raise APIException(
            f"预置关联类型「{origin['bk_asst_id']}」不可删除",
            error_code=CCErrorCode.CCErrAssociationKindPreForbidden)

    used = count_object_associations(origin['bk_asst_id'], supplier)
    if used > 0:
        raise APIException(
            f"关联类型「{origin['bk_asst_id']}」已被 {used} 个模型关联使用，"
            f"请先删除相关模型关联",
            error_code=CCErrorCode.CCErrAssociationKindHasBeenUsed)

    db_delete(TABLE, {'id': int(kind_id), 'bk_supplier_account': supplier})
    logger.info('删除关联类型 %s(id=%s)', origin['bk_asst_id'], kind_id)
    return {'id': origin['id'], 'bk_asst_id': origin['bk_asst_id'], 'deleted': True}
