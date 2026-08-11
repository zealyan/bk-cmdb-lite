from flask import Blueprint, jsonify, request
from app.service.user_service import UserService
from app.auth.identity import current_user
from app.utils.logger import get_logger

logger = get_logger('api.user')
user_bp = Blueprint('user', __name__)

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

@user_bp.route('/api/usercustom/user/search', methods=['POST'])
def search_user_custom():
    """获取用户配置"""
    try:
        # 用户名由服务端从 Bearer token 解析（current_user），不信任客户端 x-user-name 头，
        # 否则非 admin 用户（如 tom）的个性化配置会被错误归属到 admin 名下。
        user_name = current_user()
        
        config = UserService.get_user_custom(user_name)
        return success_response(config)
    except Exception as e:
        logger.error(f"Error getting user custom: {e}")
        return error_response(f'获取用户配置失败: {str(e)}')

@user_bp.route('/api/usercustom', methods=['POST'])
def save_user_custom():
    """保存用户配置"""
    try:
        # 用户名由服务端从 Bearer token 解析（current_user），不信任客户端 x-user-name 头，
        # 否则非 admin 用户（如 tom）的个性化配置会被错误归属到 admin 名下。
        user_name = current_user()
        data = request.get_json() or {}
        
        result = UserService.save_user_custom(user_name, data)
        return success_response(result, '保存用户配置成功')
    except Exception as e:
        logger.error(f"Error saving user custom: {e}")
        return error_response(f'保存用户配置失败: {str(e)}')

@user_bp.route('/api/users', methods=['GET'])
def get_users():
    """获取用户列表"""
    try:
        users = UserService.get_users()
        return success_response({'users': users})
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return error_response(f'获取用户列表失败: {str(e)}')

@user_bp.route('/api/usercustom/model/<obj_id>', methods=['GET'])
def get_model_columns(obj_id):
    """获取模型的列配置"""
    try:
        # 用户名由服务端从 Bearer token 解析（current_user），不信任客户端 x-user-name 头，
        # 否则非 admin 用户（如 tom）的个性化配置会被错误归属到 admin 名下。
        user_name = current_user()
        
        columns = UserService.get_model_columns(user_name, obj_id)
        return success_response({'columns': columns})
    except Exception as e:
        logger.error(f"Error getting model columns: {e}")
        return error_response(f'获取模型列配置失败: {str(e)}')

@user_bp.route('/api/usercustom/model/<obj_id>', methods=['POST'])
def save_model_columns(obj_id):
    """保存模型的列配置"""
    try:
        # 用户名由服务端从 Bearer token 解析（current_user），不信任客户端 x-user-name 头，
        # 否则非 admin 用户（如 tom）的个性化配置会被错误归属到 admin 名下。
        user_name = current_user()
        data = request.get_json() or {}
        columns = data.get('columns', [])
        
        result = UserService.save_model_columns(user_name, obj_id, columns)
        return success_response(result, '保存模型列配置成功')
    except Exception as e:
        logger.error(f"Error saving model columns: {e}")
        return error_response(f'保存模型列配置失败: {str(e)}')