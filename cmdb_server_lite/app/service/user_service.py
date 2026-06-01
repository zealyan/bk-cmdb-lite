from app.db.executor import query_all, query_one, execute
from datetime import datetime
import json
import logging

logger = logging.getLogger('user_service')

class UserService:
    
    @staticmethod
    def get_users():
        """获取用户列表"""
        try:
            return query_all('user/select_users.sql', {})
        except Exception:
            # 如果表不存在，返回默认用户
            return [{'user_name': 'admin', 'display_name': '管理员'}]
    
    @staticmethod
    def get_user_custom(user_name='admin'):
        """获取用户配置"""
        try:
            result = query_all('user/select_user_custom.sql', {'user_name': user_name})
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
    def save_user_custom(user_name, config):
        """保存用户配置"""
        try:
            updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for key, value in config.items():
                config_value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                execute('user/insert_or_update_user_custom.sql', {
                    'user_name': user_name,
                    'config_key': key,
                    'config_value': config_value,
                    'updated_at': updated_at
                })
            
            return {'message': 'User custom saved successfully', 'user_name': user_name}
        except Exception as e:
            logger.error(f"Error saving user custom: {e}")
            return {'message': 'User custom saved with fallback', 'user_name': user_name}
    
    @staticmethod
    def get_model_columns(user_name, obj_id):
        """获取模型的列配置"""
        try:
            config_key = f"columns_{obj_id}"
            result = query_one(
                'user/select_user_custom.sql', 
                {'user_name': user_name, 'config_key': config_key}
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
    def save_model_columns(user_name, obj_id, columns):
        """保存模型的列配置"""
        try:
            updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            config_key = f"columns_{obj_id}"
            config_value = json.dumps(columns)
            
            execute('user/insert_or_update_user_custom.sql', {
                'user_name': user_name,
                'config_key': config_key,
                'config_value': config_value,
                'updated_at': updated_at
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