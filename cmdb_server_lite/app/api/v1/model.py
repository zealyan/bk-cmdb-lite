from flask import Blueprint, jsonify, request
from app.service.model_service import ModelService
from app.service.instance_service import InstanceService
from app.service.association_service import AssociationService
from app.utils.logger import get_logger

logger = get_logger('api.model')
model_bp = Blueprint('model', __name__)

@model_bp.route('', methods=['GET'])
def get_models():
    """获取所有模型列表"""
    try:
        models = ModelService.get_all_models()
        return jsonify({'models': models})
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        return jsonify({'detail': str(e)}), 500

@model_bp.route('/<model_id>', methods=['GET'])
def get_model_by_id(model_id):
    """获取单个模型详情"""
    try:
        model = ModelService.get_model_by_id(model_id)
        if model:
            return jsonify({'model': model})
        return jsonify({'detail': 'Model not found'}), 404
    except Exception as e:
        logger.error(f"Error getting model: {e}")
        return jsonify({'detail': str(e)}), 500

@model_bp.route('/<model_id>/attributes', methods=['GET'])
def get_model_attributes(model_id):
    """获取模型属性列表"""
    try:
        attributes = ModelService.get_model_attributes(model_id)
        return jsonify({'attributes': attributes})
    except Exception as e:
        logger.error(f"Error getting model attributes: {e}")
        return jsonify({'detail': str(e)}), 500

@model_bp.route('/<model_id>/associations', methods=['GET'])
def get_model_associations(model_id):
    """获取模型的关联关系"""
    try:
        associations = AssociationService.get_model_associations(model_id)
        return jsonify({'associations': associations})
    except Exception as e:
        logger.error(f"Error getting model associations: {e}")
        return jsonify({'detail': str(e)}), 500

@model_bp.route('/<model_id>/instances', methods=['GET'])
def get_model_instances(model_id):
    """获取模型实例列表（分页）"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        conditions = {}
        search_field = request.args.get('search_field')
        search_value = request.args.get('search_value')
        
        if search_field and search_value:
            conditions[search_field] = search_value
        
        result = InstanceService.get_instances(model_id, page, page_size, conditions)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting model instances: {e}")
        return jsonify({'detail': str(e)}), 500

@model_bp.route('/<model_id>/instances/search', methods=['POST'])
def search_model_instances(model_id):
    """高级搜索模型实例"""
    try:
        data = request.get_json() or {}
        result = InstanceService.advanced_search(model_id, data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error searching model instances: {e}")
        return jsonify({'detail': str(e)}), 500

@model_bp.route('/<model_id>/instances/<instance_id>', methods=['GET'])
def get_instance(model_id, instance_id):
    """获取单个实例详情"""
    try:
        instance = InstanceService.get_instance(model_id, instance_id)
        if instance:
            return jsonify({'instance': instance})
        return jsonify({'detail': 'Instance not found'}), 404
    except Exception as e:
        logger.error(f"Error getting instance: {e}")
        return jsonify({'detail': str(e)}), 500

@model_bp.route('/<model_id>/instances', methods=['POST'])
def create_instance(model_id):
    """创建新的模型实例"""
    try:
        data = request.get_json() or {}
        instance_data = data.get('data', {})
        
        result = InstanceService.create_instance(model_id, instance_data)
        return jsonify({
            'success': True,
            'data': result,
            'message': '实例创建成功'
        }), 201
    except Exception as e:
        logger.error(f"Error creating instance: {e}")
        return jsonify({'detail': str(e)}), 500

@model_bp.route('/<model_id>/instances/<instance_id>', methods=['PUT'])
def update_instance(model_id, instance_id):
    """更新单个实例"""
    try:
        data = request.get_json() or {}
        
        result = InstanceService.update_instance(model_id, instance_id, data)
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Instance updated successfully'
        })
    except Exception as e:
        logger.error(f"Error updating instance: {e}")
        return jsonify({'detail': str(e)}), 500

@model_bp.route('/<model_id>/instances', methods=['PUT'])
def batch_update_instances(model_id):
    """批量更新实例"""
    try:
        data = request.get_json() or {}
        
        if 'update' in data:
            updated_count = 0
            for item in data['update']:
                inst_id = item.get('inst_id')
                datas = item.get('datas', {})
                if inst_id:
                    InstanceService.update_instance(model_id, inst_id, datas)
                    updated_count += 1
            return jsonify({
                'success': True,
                'updated_count': updated_count,
                'message': f'Successfully updated {updated_count} instances'
            })
        elif 'ids' in data and 'data' in data:
            ids = data['ids']
            update_data = data['data']
            updated_count = InstanceService.batch_update_instances(model_id, ids, update_data)
            return jsonify({
                'success': True,
                'updated_count': updated_count,
                'updated_ids': ids,
                'message': f'Successfully updated {updated_count} instances'
            })
        else:
            return jsonify({'detail': 'Invalid request format'}), 400
    except Exception as e:
        logger.error(f"Error updating instances: {e}")
        return jsonify({'detail': str(e)}), 500

@model_bp.route('/<model_id>/instances', methods=['DELETE'])
def delete_instances(model_id):
    """删除实例（支持批量）"""
    try:
        data = request.get_json() or {}
        ids = data.get('ids', [])
        
        if not ids:
            return jsonify({'detail': 'No instance IDs provided'}), 400
        
        deleted_count = InstanceService.delete_instances(model_id, ids)
        return jsonify({
            'deleted_count': deleted_count,
            'ids': ids,
            'message': f'Successfully deleted {deleted_count} instances'
        })
    except Exception as e:
        logger.error(f"Error deleting instances: {e}")
        return jsonify({'detail': str(e)}), 500

@model_bp.route('/<model_id>/instances/check-associations', methods=['POST'])
def check_associations(model_id):
    """检查实例关联数量"""
    try:
        data = request.get_json() or {}
        ids = data.get('ids', [])
        
        source_count = 0
        target_count = 0
        
        for instance_id in ids:
            associations = AssociationService.get_instance_associations(instance_id)
            for assoc in associations:
                if assoc.get('bk_obj_id') == model_id and assoc.get('bk_inst_id') == instance_id:
                    source_count += 1
                elif assoc.get('bk_asst_obj_id') == model_id and assoc.get('bk_asst_inst_id') == instance_id:
                    target_count += 1
        
        return jsonify({
            'total_associations': source_count + target_count,
            'source_associations': source_count,
            'target_associations': target_count,
            'instance_count': len(ids),
            'model_id': model_id
        })
    except Exception as e:
        logger.error(f"Error checking associations: {e}")
        return jsonify({'detail': str(e)}), 500

@model_bp.route('/instances/<instance_id>/associations', methods=['GET'])
def get_instance_associations(instance_id):
    """获取单个实例的关联关系"""
    try:
        associations = AssociationService.get_instance_associations(instance_id)
        return jsonify({'associations': associations})
    except Exception as e:
        logger.error(f"Error getting instance associations: {e}")
        return jsonify({'detail': str(e)}), 500

@model_bp.route('/instances/<instance_id>/related', methods=['GET'])
def get_related_instances(instance_id):
    """获取实例的关联实例详情"""
    try:
        model_id = request.args.get('model_id')
        related = InstanceService.get_related_instances(instance_id, model_id)
        return jsonify({'related': related})
    except Exception as e:
        logger.error(f"Error getting related instances: {e}")
        return jsonify({'detail': str(e)}), 500