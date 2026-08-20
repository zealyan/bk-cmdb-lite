from app.db.executor import query_all, query_one, execute
from datetime import datetime
import json
import logging

from app.db.user import ROLE_ADMIN, ROLE_NORMAL

logger = logging.getLogger('user_service')

class UserService:

    @staticmethod
    def create_user(name, password, role=ROLE_NORMAL, supplier=None):
        """创建用户（委托 app.db.user 公共逻辑层；统一输入校验 + werkzeug 哈希）。

        Args:
            name:     用户名（必填）
            password: 明文密码（长度 >= 6）
            role:     1=超管 / 2=普通用户（默认 2）
            supplier: 供应商账户（默认 settings.DEFAULT_SUPPLIER='0'）
        Returns:
            新建用户（不含密码）
        Raises:
            ValueError: 输入非法 / 用户名已存在（由 DAO 抛出）
        """
        name = (name or '').strip()
        if not name:
            raise ValueError('用户名不能为空')
        if not password or len(password) < 6:
            raise ValueError('密码长度至少 6 位')
        if role not in (ROLE_ADMIN, ROLE_NORMAL):
            raise ValueError(f'非法角色值: {role}（仅 1=超管 / 2=普通用户）')
        from app.db.user import create_user as _create_user
        return _create_user(name=name, password=password, role=role, supplier=supplier)

    @staticmethod
    def get_user(name):
        """按用户名取用户（不含密码）。"""
        from app.db.user import get_user as _get_user
        return _get_user(name)

    @staticmethod
    def list_users():
        """列出全部用户（不含密码）。"""
        from app.db.user import list_users as _list_users
        return _list_users()

    @staticmethod
    def get_users():
        """获取用户列表"""
        try:
            return query_all('user/select_users.sql', {})
        except Exception:
            # 如果表不存在，返回默认用户
            return [{'user_name': 'admin', 'display_name': '管理员'}]
    
    @staticmethod
    def get_user_custom(user_name='admin', supplier='0'):
        """获取用户配置（按 user + 租户隔离，对齐上游 cc_UserCustom）"""
        try:
            result = query_all('user/select_user_custom.sql', {'user_name': user_name, 'supplier': supplier})
            config = {}
            for row in result:
                try:
                    config[row['config_key']] = json.loads(row['config_value'])
                except (json.JSONDecodeError, TypeError):
                    config[row['config_key']] = row['config_value']
            return config
        except Exception:
            # 如果表不存在，返回空配置
            return {}
    
    @staticmethod
    def save_user_custom(user_name, config, supplier='0'):
        """保存用户配置（按 user + 租户隔离，对齐上游 cc_UserCustom）"""
        try:
            updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for key, value in config.items():
                config_value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                execute('user/insert_or_update_user_custom.sql', {
                    'user_name': user_name,
                    'config_key': key,
                    'config_value': config_value,
                    'updated_at': updated_at,
                    'supplier': supplier
                })
            
            return {'message': 'User custom saved successfully', 'user_name': user_name}
        except Exception as e:
            logger.error(f"Error saving user custom: {e}")
            return {'message': 'User custom saved with fallback', 'user_name': user_name}
    
    @staticmethod
    def get_model_columns(user_name, obj_id, supplier='0'):
        """获取模型的列配置（按 user + 租户隔离）"""
        try:
            config_key = f"{obj_id}_custom_table_columns"
            result = query_one(
                'user/select_user_custom_by_key.sql', 
                {'user_name': user_name, 'config_key': config_key, 'supplier': supplier}
            )
            if result:
                try:
                    return json.loads(result.get('config_value', '[]'))
                except json.JSONDecodeError:
                    return []
            return []
        except Exception:
            return []
    
    @staticmethod
    def save_model_columns(user_name, obj_id, columns, supplier='0'):
        """保存模型的列配置（按 user + 租户隔离）"""
        try:
            updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            config_key = f"{obj_id}_custom_table_columns"
            config_value = json.dumps(columns)
            
            execute('user/insert_or_update_user_custom.sql', {
                'user_name': user_name,
                'config_key': config_key,
                'config_value': config_value,
                'updated_at': updated_at,
                'supplier': supplier
            })
            
            return {
                'message': 'Model custom saved successfully',
                'obj_id': obj_id,
                'columns': columns
            }
        except Exception as e:
            logger.error(f"Error saving model columns: {e}")
            return {
                'message': 'Model custom saved with fallback',
                'obj_id': obj_id,
                'columns': columns
            }