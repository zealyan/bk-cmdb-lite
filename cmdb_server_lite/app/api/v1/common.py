"""
公共接口 API 模块
"""

from flask import Blueprint, jsonify, request
from app.db.executor import query_all, query_one, execute
from app.middlewares.request_mw import validate_json_params, handle_errors
from app.utils.logger import get_logger

logger = get_logger('api.common')
common_bp = Blueprint('common', __name__)

@common_bp.route('/health', methods=['GET'])
@handle_errors
def health_check():
    """健康检查"""
    try:
        # 检查数据库连接
        result = query_one("SELECT 1 as health")
        db_status = "connected" if result else "error"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return jsonify({
        'status': 'healthy' if db_status == 'connected' else 'unhealthy',
        'service': 'CMDB Server Lite',
        'version': '1.0.0',
        'database': {
            'status': db_status
        }
    })

@common_bp.route('/statistics', methods=['GET'])
@handle_errors
def get_statistics():
    """获取统计数据"""
    try:
        # 获取模型数量
        models = query_all("SELECT DISTINCT bk_obj_id FROM cc_ObjAttDes")
        
        stats = {
            'total_models': len(models),
            'models': []
        }
        
        for model in models:
            model_id = model['bk_obj_id']
            table_name = f"cc_ObjectBase_0_pub_{model_id}"
            try:
                result = query_one(f'SELECT COUNT(*) as cnt FROM "{table_name}"')
                count = result.get('cnt', 0) if result else 0
                stats['models'].append({
                    'model_id': model_id,
                    'instance_count': count
                })
            except:
                pass
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({'error': str(e)}), 500
