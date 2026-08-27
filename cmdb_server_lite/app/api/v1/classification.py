from flask import Blueprint, jsonify, request
from app.service.classification_service import ClassificationService
from app.utils.logger import get_logger

logger = get_logger('api.classification')
classification_bp = Blueprint('classification', __name__)

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

@classification_bp.route('', methods=['GET'])
def get_classifications():
    """获取所有分类列表"""
    try:
        classifications = ClassificationService.get_all_classifications()
        return success_response({'classifications': classifications})
    except Exception as e:
        logger.error(f"Error getting classifications: {e}")
        return error_response(f'获取分类列表失败: {str(e)}')

@classification_bp.route('/find/classificationobject', methods=['POST'])
def find_classification_objects():
    """查询分类及其下属模型"""
    try:
        # 尝试获取 JSON 数据，如果失败则忽略（处理 Content-Type 问题）
        try:
            data = request.get_json()
        except:
            data = {}
        
        classifications = ClassificationService.get_classifications_with_models()
        return success_response(classifications)
    except Exception as e:
        logger.error(f"Error finding classification objects: {e}")
        return error_response(f'查询分类失败: {str(e)}')

@classification_bp.route('/<classification_id>', methods=['GET'])
def get_classification_by_id(classification_id):
    """获取单个分类详情"""
    try:
        classification = ClassificationService.get_classification_by_id(classification_id)
        if classification:
            return success_response({'classification': classification})
        return error_response(f'分类 {classification_id} 不存在', 1199019)
    except Exception as e:
        logger.error(f"Error getting classification: {e}")
        return error_response(f'获取分类失败: {str(e)}')

@classification_bp.route('/<classification_id>/models', methods=['GET'])
def get_classification_models(classification_id):
    """获取分类下的所有模型"""
    try:
        models = ClassificationService.get_models_by_classification(classification_id)
        return success_response({'models': models})
    except Exception as e:
        logger.error(f"Error getting classification models: {e}")
        return error_response(f'获取分类模型失败: {str(e)}')