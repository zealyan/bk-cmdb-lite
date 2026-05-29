from app.db.executor import query_all, query_one, execute
from datetime import datetime
import json

class UserService:
    
    @staticmethod
    def get_users():
        """获取用户列表"""
        return query_all('user/select_users.sql', {})
    
    @staticmethod
    def get_user_custom(user_name='admin'):
        """获取用户配置"""
        result = query_all('user/select_user_custom.sql', {'user_name': user_name})
        config = {}
        for row in result:
            try:
                config[row['config_key']] = json.loads(row['config_value'])
            except (json.JSONDecodeError, TypeError):
                config[row['config_key']] = row['config_value']
        return config
    
    @staticmethod
    def save_user_custom(user_name, config):
        """保存用户配置"""
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
    
    @staticmethod
    def get_model_columns(user_name, obj_id):
        """获取模型的列配置"""
        config_key = f"columns_{obj_id}"
        result = query_one(
            'user/select_user_custom.sql', 
            {'user_name': user_name}
        )
        if result:
            try:
                return json.loads(result.get('config_value', '[]'))
            except json.JSONDecodeError:
                return []
        return []
    
    @staticmethod
    def save_model_columns(user_name, obj_id, columns):
        """保存模型的列配置"""
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