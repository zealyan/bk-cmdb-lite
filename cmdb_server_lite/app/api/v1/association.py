from flask import Blueprint, jsonify, request
from app.auth.identity import current_supplier, current_user
from app.service import association_type_service as kind_svc
from app.service.association_service import AssociationService
from app.service.instance_service import InstanceService
from app.utils.logger import get_logger
from app.utils.exceptions import ValidationException, APIException, CCErrorCode

logger = get_logger('api.association')
association_bp = Blueprint('association', __name__)

def error_response(message, error_code=1199999):
    """统一错误响应格式 - 与原项目 BaseResp 一致"""
    return jsonify({
        'result': False,
        'bk_error_code': error_code,
        'bk_error_msg': message
    }), 200

def success_response(data=None, message=''):
    """统一成功响应格式 - 与原项目 BaseResp 一致"""
    if data is None:
        data = {}
    return jsonify({
        'result': True,
        'bk_error_code': 0,
        'bk_error_msg': message,
        'data': data
    }), 200

@association_bp.route('/find/<obj_id>', methods=['POST'])
def find_instances(obj_id):
    """查询实例（旧版兼容接口）"""
    try:
        data = request.get_json() or {}
        condition = data.get('condition', {})
        
        if 'id' in condition:
            instance_id = condition.get('id')
            instance = InstanceService.get_instance(obj_id, instance_id)
            if instance:
                return success_response(instance)
            return success_response({})
        
        instances = InstanceService.get_instances(obj_id, 1, 100, condition)
        return success_response(instances)
    except Exception as e:
        logger.error(f"Error finding instances for {obj_id}: {e}")
        return error_response(f'查询实例失败: {str(e)}')

def _kind_supplier():
    """本次请求的供应商账户：请求体/查询串优先，其次当前身份（默认 '0'）。"""
    payload = request.get_json(silent=True) or {}
    return (payload.get('bk_supplier_account')
            or request.args.get('bk_supplier_account')
            or current_supplier() or '0')


@association_bp.route('/find/associationtype', methods=['POST'])
def find_association_type():
    """查询关联类型（含 direction / src_des / dest_des / direction_label）。

    对齐上游 topo_server POST /find/associationtype。
    出参 data.info[*]：
      bk_asst_id / bk_asst_name / src_des（源→目标描述）/ dest_des（目标→源描述）
      / direction（none|src_to_dest|dest_to_src|bidirectional）/ direction_label（中文）
      / ispre(bool) / id(int)
    """
    try:
        types = AssociationService.get_association_types(_kind_supplier())
        return success_response({'info': types, 'count': len(types)})
    except APIException:
        raise
    except Exception as e:
        logger.error(f"Error finding association types: {e}")
        return error_response(f'查询关联类型失败: {str(e)}')


@association_bp.route('/create/associationtype', methods=['POST'])
def create_association_type():
    """创建关联类型（对齐上游 POST /create/associationtype）。

    请求体：
      - bk_asst_id    必填，唯一标识（^[a-zA-Z]\\w*$，≤128）
      - bk_asst_name  必填，显示名
      - src_des       选填，源→目标 描述（如「访问」）
      - dest_des      选填，目标→源 描述（如「被访问」）
      - direction     选填，方向；缺省 src_to_dest
                      none=无方向 / src_to_dest=源到目标 / dest_to_src=目标到源
                      / bidirectional=双向
      - bk_asst_icon  选填，图标
    ispre 由服务层恒置 False（预置标记仅 migrate 可写）。
    """
    try:
        data = request.get_json(silent=True) or {}
        created = kind_svc.create_association_type(
            data, supplier=_kind_supplier(), operator=current_user())
        return success_response(created, '关联类型创建成功')
    except APIException as e:
        return error_response(e.message, e.error_code)
    except Exception as e:
        logger.error(f"Error creating association type: {e}")
        return error_response(f'创建关联类型失败: {str(e)}')


@association_bp.route('/update/associationtype/<int:kind_id>', methods=['PUT'])
def update_association_type(kind_id):
    """更新关联类型（对齐上游 PUT /update/associationtype/{id}）。

    仅 bk_asst_name / src_des / dest_des / direction 可改；
    未传的字段保留原值；id / bk_asst_id / ispre 传了也会被忽略。
    """
    try:
        data = request.get_json(silent=True) or {}
        updated = kind_svc.update_association_type(
            kind_id, data, supplier=_kind_supplier(), operator=current_user())
        return success_response(updated, '关联类型更新成功')
    except APIException as e:
        return error_response(e.message, e.error_code)
    except Exception as e:
        logger.error(f"Error updating association type {kind_id}: {e}")
        return error_response(f'更新关联类型失败: {str(e)}')


@association_bp.route('/delete/associationtype/<int:kind_id>', methods=['DELETE'])
def delete_association_type(kind_id):
    """删除关联类型（对齐上游 DELETE /delete/associationtype/{id}）。

    双重保护：预置类型（ispre）禁删；已被模型关联（cc_ObjAsst）引用的类型禁删。
    """
    try:
        result = kind_svc.delete_association_type(kind_id, supplier=_kind_supplier())
        return success_response(result, '关联类型删除成功')
    except APIException as e:
        return error_response(e.message, e.error_code)
    except Exception as e:
        logger.error(f"Error deleting association type {kind_id}: {e}")
        return error_response(f'删除关联类型失败: {str(e)}')

@association_bp.route('/find/objectassociation', methods=['POST'])
def find_object_association():
    """查询对象关联"""
    try:
        data = request.get_json() or {}
        conditions = data.get('condition', {})
        
        associations = AssociationService.get_object_associations(conditions)
        return success_response(associations)
    except Exception as e:
        logger.error(f"Error finding object associations: {e}")
        return error_response(f'查询对象关联失败: {str(e)}')

@association_bp.route('/create/objectassociation', methods=['POST'])
def create_object_association():
    """创建通用（非主线）模型关联，幂等。

    请求体（字段对齐前端通用关联语义）：
      - bk_obj_id / src_obj_id   : 源模型ID（必填）
      - target_obj_id / bk_asst_obj_id : 目标模型ID（必填）
      - bk_asst_id               : 关联类型ID（必填，须存在于 cc_AsstDes，且非 bk_mainline）
      - mapping                  : 1:1 / 1:n / n:1 / n:n（默认 1:n）
      - on_delete                : none / ...（默认 none）
      - bk_obj_asst_name         : 显示名（缺省由关联类型与模型名拼接）
      - on_exist                 : skip（默认，已存在则跳过）/ update（已存在则更新 mapping/on_delete）
    返回 AssociationService.create_model_association 的结果。
    """
    try:
        data = request.get_json() or {}
        src = data.get('bk_obj_id') or data.get('src_obj_id')
        dst = data.get('target_obj_id') or data.get('bk_asst_obj_id')
        asst_id = data.get('bk_asst_id')
        if not (src and dst and asst_id):
            return error_response(
                'bk_obj_id(源模型)、target_obj_id(目标模型)、bk_asst_id(关联类型) 必填', 1199006)
        result = AssociationService.create_model_association(
            src_obj_id=src, dst_obj_id=dst, asst_id=asst_id,
            mapping=data.get('mapping', '1:n'),
            on_delete=data.get('on_delete', 'none'),
            asst_name=data.get('bk_obj_asst_name'),
            supplier=data.get('bk_supplier_account', '0'),
            on_exist=data.get('on_exist', 'skip'))
        msg = '模型关联创建成功' if result['created'] else '模型关联已存在（幂等跳过）'
        return success_response(result, msg)
    except ValueError as e:
        return error_response(str(e), 1199006)
    except Exception as e:
        logger.error(f"Error creating object association: {e}")
        return error_response(f'创建模型关联失败: {str(e)}')

@association_bp.route('/delete/objectassociation', methods=['POST'])
def delete_object_association():
    """删除通用（非主线）模型关联，级联清理实例关联。

    请求体（二选一）：
      - bk_obj_asst_id            : 直接给主键（优先）
      - 或 (bk_obj_id/src_obj_id, target_obj_id/bk_asst_obj_id, bk_asst_id) 三元组
    禁止删除 bk_mainline 主线关联（由专用接口处理）。
    """
    try:
        data = request.get_json() or {}
        bk_obj_asst_id = data.get('bk_obj_asst_id')
        src = data.get('bk_obj_id') or data.get('src_obj_id')
        dst = data.get('target_obj_id') or data.get('bk_asst_obj_id')
        asst_id = data.get('bk_asst_id')
        result = AssociationService.delete_model_association(
            src_obj_id=src, dst_obj_id=dst, asst_id=asst_id,
            bk_obj_asst_id=bk_obj_asst_id,
            supplier=data.get('bk_supplier_account', '0'))
        msg = '模型关联删除成功' if result['deleted'] else '模型关联不存在'
        return success_response(result, msg)
    except ValueError as e:
        return error_response(str(e), 1199006)
    except Exception as e:
        logger.error(f"Error deleting object association: {e}")
        return error_response(f'删除模型关联失败: {str(e)}')

# 说明：实例关联查询（GET /api/v1/instances/<id>/associations）与关联实例详情
# （GET /api/v1/instances/<id>/related）统一由 model.py 的 instance_bp 提供，
# 此处原有的 /api/instances/... 两个同名路由属重复实现且从未被前端调用（前端一直
# 走 /api/v1/instances/...），已在 API 前缀对齐时移除，避免加 /api/v1 前缀后与
# instance_bp 产生同 URL 双 endpoint 的隐蔽冲突。
@association_bp.route('/associations/candidates', methods=['POST'])
def search_association_candidates():
    """查询「新增关联」弹框的候选目标实例（支持 全部/已关联/未关联 筛选 + 条件 + 排序 + 分页组合查询）"""
    try:
        data = request.get_json() or {}
        obj_id = data.get('obj_id')
        inst_id = data.get('inst_id')
        asst_obj_id = data.get('asst_obj_id')
        bk_obj_asst_id = data.get('bk_obj_asst_id')
        if not (obj_id and inst_id is not None and asst_obj_id and bk_obj_asst_id):
            return error_response('缺少必要参数：obj_id / inst_id / asst_obj_id / bk_obj_asst_id', 1199006)
        result = AssociationService.search_candidates(data)
        return success_response(result)
    except Exception as e:
        logger.error(f"Error searching association candidates: {e}")
        return error_response(f'查询候选关联实例失败: {str(e)}')

@association_bp.route('/create/instassociation', methods=['POST'])
def create_instassociation():
    """创建实例关联"""
    try:
        data = request.get_json() or {}
        
        result = AssociationService.create_instance_association(data)
        return success_response(result, '关联创建成功')
    except ValueError as e:
        logger.error(f"Validation error creating instance association: {e}")
        return error_response(str(e), 1199006)
    except Exception as e:
        logger.error(f"Error creating instance association: {e}")
        return error_response(f'创建关联失败: {str(e)}')

@association_bp.route('/delete/instassociation/<obj_id>/<inst_asst_id>', methods=['DELETE'])
def delete_instassociation(obj_id, inst_asst_id):
    """删除实例关联"""
    try:
        result = AssociationService.delete_instance_association(inst_asst_id, obj_id)
        return success_response(result, '关联删除成功')
    except Exception as e:
        logger.error(f"Error deleting instance association: {e}")
        return error_response(f'删除关联失败: {str(e)}')

@association_bp.route('/find/instassociation', methods=['POST'])
def find_instassociation():
    """查询实例关联"""
    try:
        data = request.get_json() or {}
        bk_obj_id = data.get('bk_obj_id', '')
        conditions = data.get('condition', {})
        
        associations = AssociationService.find_instance_associations(bk_obj_id, conditions)
        return success_response({'info': associations})
    except Exception as e:
        logger.error(f"Error finding instance associations: {e}")
        return error_response(f'查询实例关联失败: {str(e)}')

