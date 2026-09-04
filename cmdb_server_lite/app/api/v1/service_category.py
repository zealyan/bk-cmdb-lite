"""
服务分类（ServiceCategory）API 路由

对齐蓝鲸 CMDB 进程内「服务分类」管理（src/source_controller/coreservice/.../process/）：
  - GET    /api/v1/service/category?bk_biz_id=&bk_supplier_account=  查询某业务分类列表（扁平）
  - GET    /api/v1/service/category/<id>                            查询单个分类（含一级/二级路径）
  - POST   /api/v1/service/category                                 创建（一级 / 二级）
  - PUT    /api/v1/service/category/<id>                            重命名
  - DELETE /api/v1/service/category/<id>                            删除（有子分类则禁止，须先清空二级）

两级树关系由 bk_parent_id / bk_root_id 表达，前端按此组装。bk_supplier_account
用于多租户隔离，缺省 '0'。
"""
from flask import Blueprint, request, jsonify
from app.service import service_category_service as svc
from app.utils.exceptions import APIException, CCErrorCode

service_category_bp = Blueprint('service_category', __name__)


def _biz_id() -> int:
    payload = request.get_json(silent=True) or {}
    biz = payload.get('bk_biz_id') or request.args.get('bk_biz_id')
    if biz in (None, ''):
        raise APIException('缺少业务ID参数 bk_biz_id', error_code=CCErrorCode.CCErrCommParamsInvalid)
    try:
        return int(biz)
    except (TypeError, ValueError):
        raise APIException('bk_biz_id 必须是整数', error_code=CCErrorCode.CCErrCommParamsInvalid)


def _supplier() -> str:
    payload = request.get_json(silent=True) or {}
    return (payload.get('bk_supplier_account')
            or request.args.get('bk_supplier_account')
            or '0').strip() or '0'


@service_category_bp.route('', methods=['GET'])
def list_service_categories():
    """查询某业务下的服务分类列表（扁平）。"""
    biz_id = _biz_id()
    supplier = _supplier()
    try:
        rows = svc.list_categories(biz_id, supplier)
        return jsonify({
            'result': True,
            'bk_error_code': 0,
            'bk_error_msg': '',
            'data': {'info': [_to_dict(r) for r in rows], 'count': len(rows)}
        })
    except APIException:
        raise
    except Exception as e:  # noqa: BLE001
        raise APIException(f'查询服务分类失败: {str(e)}', error_code=CCErrorCode.CCErrCommInternalServerError)


@service_category_bp.route('', methods=['POST'])
def create_service_category():
    """创建服务分类。

    Body: { bk_biz_id, name, bk_parent_id? }
      - bk_parent_id 缺省 / 0 → 一级分类；
      - 非 0 → 二级分类（父级须为本业务同租户的一级分类）。
    """
    payload = request.get_json(silent=True) or {}
    biz_id = _biz_id()
    supplier = _supplier()
    name = (payload.get('name') or '').strip()
    parent_id = int(payload.get('bk_parent_id') or 0)
    try:
        created = svc.create_category(biz_id, name, parent_id, supplier)
        return jsonify({
            'result': True,
            'bk_error_code': 0,
            'bk_error_msg': '',
            'data': created
        })
    except APIException:
        raise
    except Exception as e:  # noqa: BLE001
        raise APIException(f'创建服务分类失败: {str(e)}', error_code=CCErrorCode.CCErrCommInternalServerError)


@service_category_bp.route('/<int:cat_id>', methods=['GET'])
def get_service_category(cat_id):
    """按 id 查询单个分类，含两级路径（一级 / 二级名称）。

    用于业务拓扑「节点信息」tab 展示模块所属服务分类：
    「服务分类：一级分类 / 二级分类」。仅按 bk_supplier_account 隔离查询。
    """
    supplier = _supplier()
    try:
        cat = svc.get_category_with_path(cat_id, supplier)
        return jsonify({
            'result': True,
            'bk_error_code': 0,
            'bk_error_msg': '',
            'data': cat
        })
    except APIException:
        raise
    except Exception as e:  # noqa: BLE001
        raise APIException(f'查询服务分类失败: {str(e)}', error_code=CCErrorCode.CCErrCommInternalServerError)


@service_category_bp.route('/<int:cat_id>', methods=['PUT'])
def update_service_category(cat_id):
    """重命名服务分类。Body: { name }"""
    payload = request.get_json(silent=True) or {}
    supplier = _supplier()
    name = (payload.get('name') or '').strip()
    try:
        updated = svc.update_category(cat_id, name, supplier)
        return jsonify({
            'result': True,
            'bk_error_code': 0,
            'bk_error_msg': '',
            'data': updated
        })
    except APIException:
        raise
    except Exception as e:  # noqa: BLE001
        raise APIException(f'更新服务分类失败: {str(e)}', error_code=CCErrorCode.CCErrCommInternalServerError)


@service_category_bp.route('/<int:cat_id>', methods=['DELETE'])
def delete_service_category(cat_id):
    """删除服务分类（内置分类不可删；一级分类下存在二级分类时禁止删除）。"""
    supplier = _supplier()
    try:
        affected = svc.delete_category(cat_id, supplier)
        return jsonify({
            'result': True,
            'bk_error_code': 0,
            'bk_error_msg': '',
            'data': {'deleted': affected}
        })
    except APIException:
        raise
    except Exception as e:  # noqa: BLE001
        raise APIException(f'删除服务分类失败: {str(e)}', error_code=CCErrorCode.CCErrCommInternalServerError)


def _to_dict(row: dict) -> dict:
    """将 DB 行规整为前端友好的字典（字段名与上游 ServiceCategory 对齐）。"""
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
