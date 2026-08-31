from flask import Blueprint, jsonify, request
from app.service.association_service import AssociationService
from app.service.instance_service import InstanceService
from app.utils.logger import get_logger
from app.utils.exceptions import ValidationException, APIException

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

@association_bp.route('/find/associationtype', methods=['POST'])
def find_association_type():
    """查询关联类型"""
    try:
        data = request.get_json() or {}
        types = AssociationService.get_association_types()
        return success_response({'info': types})
    except Exception as e:
        logger.error(f"Error finding association types: {e}")
        return error_response(f'查询关联类型失败: {str(e)}')

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

@association_bp.route('/api/instances/<instance_id>/associations', methods=['GET'])
def get_instance_associations(instance_id):
    """获取实例的关联关系"""
    try:
        obj_id = request.args.get('obj_id')
        associations = AssociationService.get_instance_associations(instance_id, obj_id)
        return success_response({'associations': associations})
    except Exception as e:
        logger.error(f"Error getting instance associations: {e}")
        return error_response(f'获取关联关系失败: {str(e)}')

@association_bp.route('/api/v1/associations/candidates', methods=['POST'])
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

@association_bp.route('/api/instances/<instance_id>/related', methods=['GET'])
def get_related_instances(instance_id):
    """获取实例的相关实例"""
    try:
        model_id = request.args.get('model_id')
        
        related = AssociationService.get_related_instances(instance_id, model_id)
        return success_response({'related': related})
    except Exception as e:
        logger.error(f"Error getting related instances: {e}")
        return error_response(f'获取关联实例失败: {str(e)}')