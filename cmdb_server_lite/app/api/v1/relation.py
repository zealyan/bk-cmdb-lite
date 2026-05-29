from flask import Blueprint, jsonify
from app.service.relation_service import RelationService
from app.utils.logger import get_logger

logger = get_logger('api.relation')
relation_bp = Blueprint('relation', __name__)

@relation_bp.route('', methods=['GET'])
def get_relations():
    """获取所有关系类型"""
    try:
        relations = RelationService.get_all_relations()
        return jsonify({'relations': relations})
    except Exception as e:
        logger.error(f"Error getting relations: {e}")
        return jsonify({'detail': str(e)}), 500