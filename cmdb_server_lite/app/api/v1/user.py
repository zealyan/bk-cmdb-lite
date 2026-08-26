from flask import Blueprint, jsonify, request
from app.service.user_service import UserService
from app.auth.identity import current_user, current_user_payload, current_supplier
from app.config.settings import get_config
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
        supplier = current_supplier()

        config = UserService.get_user_custom(user_name, supplier)
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
        supplier = current_supplier()
        data = request.get_json() or {}
        
        result = UserService.save_user_custom(user_name, data, supplier)
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

@user_bp.route('/api/users', methods=['POST'])
def create_user():
    """创建用户（暂无 UI，供 CLI / 运维 / 后续前端调用）"""
    try:
        cfg = get_config()
        # ENABLE_AUTH 开启时仅超级管理员可创建；关闭（dev / skipLogin）放行以保持友好。
        if cfg.ENABLE_AUTH:
            payload = current_user_payload() or {}
            if payload.get('bk_role') != 1:
                return error_response('仅超级管理员可创建用户', cfg.AUTH_ERR_NO_PERMISSION)

        data = request.get_json() or {}
        name = data.get('bk_user_name') or data.get('name') or ''
        password = data.get('bk_password') or data.get('password') or ''
        role = int(data.get('bk_role', data.get('role', 2) or 2))
        supplier = data.get('bk_supplier_account') or data.get('supplier') or cfg.DEFAULT_SUPPLIER

        user = UserService.create_user(name=name, password=password, role=role, supplier=supplier)
        return success_response(user, '创建用户成功')
    except ValueError as e:
        # 输入非法 / 用户名已存在
        return error_response(str(e), 1199100)
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return error_response(f'创建用户失败: {str(e)}')

@user_bp.route('/api/usercustom/model/<obj_id>', methods=['GET'])
def get_model_columns(obj_id):
    """获取模型的列配置"""
    try:
        # 用户名由服务端从 Bearer token 解析（current_user），不信任客户端 x-user-name 头，
        # 否则非 admin 用户（如 tom）的个性化配置会被错误归属到 admin 名下。
        user_name = current_user()
        supplier = current_supplier()
        
        columns = UserService.get_model_columns(user_name, obj_id, supplier)
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
        supplier = current_supplier()
        data = request.get_json() or {}
        columns = data.get('columns', [])
        
        result = UserService.save_model_columns(user_name, obj_id, columns, supplier)
        return success_response(result, '保存模型列配置成功')
    except Exception as e:
        logger.error(f"Error saving model columns: {e}")
        return error_response(f'保存模型列配置失败: {str(e)}')