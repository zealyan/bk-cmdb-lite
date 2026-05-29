from flask import Blueprint, jsonify, request
from app.service.user_service import UserService
from app.utils.logger import get_logger

logger = get_logger('api.user')
user_bp = Blueprint('user', __name__)

@user_bp.route('/api/usercustom/user/search', methods=['POST'])
def search_user_custom():
    """获取用户配置"""
    try:
        user_name = request.headers.get('x-user-name', 'admin')
        
        config = UserService.get_user_custom(user_name)
        return jsonify(config)
    except Exception as e:
        logger.error(f"Error getting user custom: {e}")
        return jsonify({'detail': str(e)}), 500

@user_bp.route('/api/usercustom', methods=['POST'])
def save_user_custom():
    """保存用户配置"""
    try:
        user_name = request.headers.get('x-user-name', 'admin')
        data = request.get_json() or {}
        
        result = UserService.save_user_custom(user_name, data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error saving user custom: {e}")
        return jsonify({'detail': str(e)}), 500

@user_bp.route('/api/users', methods=['GET'])
def get_users():
    """获取用户列表"""
    try:
        users = UserService.get_users()
        return jsonify({'users': users})
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({'detail': str(e)}), 500

@user_bp.route('/api/usercustom/model/<obj_id>', methods=['GET'])
def get_model_columns(obj_id):
    """获取模型的列配置"""
    try:
        user_name = request.headers.get('x-user-name', 'admin')
        
        columns = UserService.get_model_columns(user_name, obj_id)
        return jsonify({'columns': columns})
    except Exception as e:
        logger.error(f"Error getting model columns: {e}")
        return jsonify({'detail': str(e)}), 500

@user_bp.route('/api/usercustom/model/<obj_id>', methods=['POST'])
def save_model_columns(obj_id):
    """保存模型的列配置"""
    try:
        user_name = request.headers.get('x-user-name', 'admin')
        data = request.get_json() or {}
        columns = data.get('columns', [])
        
        result = UserService.save_model_columns(user_name, obj_id, columns)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error saving model columns: {e}")
        return jsonify({'detail': str(e)}), 500