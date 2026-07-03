from flask import Blueprint, request, jsonify
from app.service.model_service import ModelService
import json

unique_bp = Blueprint('unique', __name__)


@unique_bp.route('/find/objectunique/object/<model_id>', methods=['POST'])
def search_object_unique(model_id):
    """
    查询模型的唯一约束
    POST /find/objectunique/object/<model_id>
    
    请求体:
    []
    
    返回:
    {
        "count": int,
        "info": [
            {
                "id": int,
                "bk_obj_id": string,
                "keys": [{"key_kind": "property", "key_id": int}],
                "ispre": bool,
                "bk_supplier_account": string
            }
        ]
    }
    """
    result = ModelService.get_object_unique(model_id)
    return jsonify({
        'count': len(result),
        'info': result
    }), 200


@unique_bp.route('/create/objectunique/object/<model_id>', methods=['POST'])
def create_object_unique(model_id):
    """
    创建模型的唯一约束
    POST /create/objectunique/object/<model_id>
    
    请求体:
    {
        "keys": [{"key_kind": "property", "key_id": int}]
    }
    """
    data = request.get_json() or {}
    keys = data.get('keys', [])
    
    if not isinstance(keys, list) or len(keys) == 0:
        return jsonify({'error': 'keys must be a non-empty list'}), 400
    
    for key in keys:
        if key.get('key_kind') != 'property':
            return jsonify({'error': 'only property key_kind is supported'}), 400
        if not isinstance(key.get('key_id'), int):
            return jsonify({'error': 'key_id must be an integer'}), 400
    
    unique_id = ModelService.create_object_unique(model_id, keys)
    
    return jsonify({
        'code': 0,
        'data': {'id': unique_id}
    }), 200


@unique_bp.route('/update/objectunique/object/<model_id>/unique/<int:unique_id>', methods=['PUT'])
def update_object_unique(model_id, unique_id):
    """
    更新模型的唯一约束
    PUT /update/objectunique/object/<model_id>/unique/<unique_id>
    
    请求体:
    {
        "keys": [{"key_kind": "property", "key_id": int}]
    }
    """
    data = request.get_json() or {}
    keys = data.get('keys', [])
    
    if not isinstance(keys, list) or len(keys) == 0:
        return jsonify({'error': 'keys must be a non-empty list'}), 400
    
    success = ModelService.update_object_unique(model_id, unique_id, keys)
    
    if not success:
        return jsonify({'error': 'unique constraint not found'}), 404
    
    return jsonify({'code': 0}), 200


@unique_bp.route('/delete/objectunique/object/<model_id>/unique/<int:unique_id>', methods=['POST'])
def delete_object_unique(model_id, unique_id):
    """
    删除模型的唯一约束
    POST /delete/objectunique/object/<model_id>/unique/<unique_id>
    """
    success = ModelService.delete_object_unique(model_id, unique_id)
    
    if not success:
        return jsonify({'error': 'unique constraint not found'}), 404
    
    return jsonify({'code': 0}), 200
