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
    """统一成功响应 - 直接返回业务数据（与原项目一致）"""
    if data is None:
        data = {}
    return jsonify(data), 200

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