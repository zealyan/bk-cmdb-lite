from flask import Blueprint, jsonify, request
from app.service.association_service import AssociationService
from app.service.instance_service import InstanceService
from app.utils.logger import get_logger

logger = get_logger('api.association')
association_bp = Blueprint('association', __name__)

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
                return jsonify(instance)
            return jsonify({})
        
        instances = InstanceService.get_instances(obj_id, 1, 100, condition)
        return jsonify(instances)
    except Exception as e:
        logger.error(f"Error finding instances for {obj_id}: {e}")
        return jsonify({'detail': str(e)}), 500

@association_bp.route('/find/associationtype', methods=['POST'])
def find_association_type():
    """查询关联类型"""
    try:
        data = request.get_json() or {}
        types = AssociationService.get_association_types()
        return jsonify({'info': types})
    except Exception as e:
        logger.error(f"Error finding association types: {e}")
        return jsonify({'detail': str(e)}), 500

@association_bp.route('/find/objectassociation', methods=['POST'])
def find_object_association():
    """查询对象关联"""
    try:
        data = request.get_json() or {}
        conditions = data.get('condition', {})
        
        associations = AssociationService.get_object_associations(conditions)
        return jsonify(associations)
    except Exception as e:
        logger.error(f"Error finding object associations: {e}")
        return jsonify({'detail': str(e)}), 500

@association_bp.route('/api/instances/<instance_id>/associations', methods=['GET'])
def get_instance_associations(instance_id):
    """获取实例的关联关系"""
    try:
        associations = AssociationService.get_instance_associations(instance_id)
        return jsonify({'associations': associations})
    except Exception as e:
        logger.error(f"Error getting instance associations: {e}")
        return jsonify({'detail': str(e)}), 500

@association_bp.route('/create/instassociation', methods=['POST'])
def create_instassociation():
    """创建实例关联"""
    try:
        data = request.get_json() or {}
        
        result = AssociationService.create_instance_association(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error creating instance association: {e}")
        return jsonify({'detail': str(e)}), 500

@association_bp.route('/delete/instassociation/<obj_id>/<inst_asst_id>', methods=['DELETE'])
def delete_instassociation(obj_id, inst_asst_id):
    """删除实例关联"""
    try:
        result = AssociationService.delete_instance_association(inst_asst_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error deleting instance association: {e}")
        return jsonify({'detail': str(e)}), 500

@association_bp.route('/find/instassociation', methods=['POST'])
def find_instassociation():
    """查询实例关联"""
    try:
        data = request.get_json() or {}
        bk_obj_id = data.get('bk_obj_id', '')
        conditions = data.get('condition', {})
        
        associations = AssociationService.find_instance_associations(bk_obj_id, conditions)
        return jsonify({'info': associations})
    except Exception as e:
        logger.error(f"Error finding instance associations: {e}")
        return jsonify({'detail': str(e)}), 500

@association_bp.route('/api/instances/<instance_id>/related', methods=['GET'])
def get_related_instances(instance_id):
    """获取实例的相关实例"""
    try:
        model_id = request.args.get('model_id')
        
        related = AssociationService.get_related_instances(instance_id, model_id)
        return jsonify({'related': related})
    except Exception as e:
        logger.error(f"Error getting related instances: {e}")
        return jsonify({'detail': str(e)}), 500