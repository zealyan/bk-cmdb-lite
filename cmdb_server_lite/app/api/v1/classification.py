from flask import Blueprint, jsonify, request
from app.service.classification_service import ClassificationService
from app.utils.logger import get_logger

logger = get_logger('api.classification')
classification_bp = Blueprint('classification', __name__)

@classification_bp.route('', methods=['GET'])
def get_classifications():
    """获取所有分类列表"""
    try:
        classifications = ClassificationService.get_all_classifications()
        return jsonify({'classifications': classifications})
    except Exception as e:
        logger.error(f"Error getting classifications: {e}")
        return jsonify({'detail': str(e)}), 500

@classification_bp.route('/find/classificationobject', methods=['POST'])
def find_classification_objects():
    """查询分类及其下属模型"""
    try:
        data = request.get_json() or {}
        classifications = ClassificationService.get_classifications_with_models()
        return jsonify(classifications)
    except Exception as e:
        logger.error(f"Error finding classification objects: {e}")
        return jsonify({'detail': str(e)}), 500

@classification_bp.route('/<classification_id>', methods=['GET'])
def get_classification_by_id(classification_id):
    """获取单个分类详情"""
    try:
        classification = ClassificationService.get_classification_by_id(classification_id)
        if classification:
            return jsonify({'classification': classification})
        return jsonify({'detail': 'Classification not found'}), 404
    except Exception as e:
        logger.error(f"Error getting classification: {e}")
        return jsonify({'detail': str(e)}), 500

@classification_bp.route('/<classification_id>/models', methods=['GET'])
def get_classification_models(classification_id):
    """获取分类下的所有模型"""
    try:
        models = ClassificationService.get_models_by_classification(classification_id)
        return jsonify({'models': models})
    except Exception as e:
        logger.error(f"Error getting classification models: {e}")
        return jsonify({'detail': str(e)}), 500