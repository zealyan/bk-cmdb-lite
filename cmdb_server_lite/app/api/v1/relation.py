from flask import Blueprint, jsonify
from app.service.relation_service import RelationService
from app.utils.logger import get_logger

logger = get_logger('api.relation')
relation_bp = Blueprint('relation', __name__)

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

@relation_bp.route('', methods=['GET'])
def get_relations():
    """获取所有关系类型"""
    try:
        relations = RelationService.get_all_relations()
        return success_response({'relations': relations})
    except Exception as e:
        logger.error(f"Error getting relations: {e}")
        return error_response(f'获取关系类型失败: {str(e)}')