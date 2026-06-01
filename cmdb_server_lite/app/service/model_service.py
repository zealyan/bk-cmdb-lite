from app.db.executor import query_all, query_one
import json

class ModelService:
    
    @staticmethod
    def get_all_models():
        """获取所有模型"""
        return query_all('model/select_models.sql', {})
    
    @staticmethod
    def get_model_by_id(model_id):
        """获取模型详情"""
        return query_one('model/select_model_by_id.sql', {
            'model_id': model_id
        })
    
    @staticmethod
    def get_model_attributes(model_id):
        """获取模型属性"""
        attributes = query_all('model/select_model_attributes.sql', {
            'model_id': model_id
        })
        
        # 处理 option 字段的反序列化
        for attr in attributes:
            option = attr.get('option')
            if option:
                try:
                    # 尝试解析为 JSON
                    parsed_option = json.loads(option)
                    attr['option'] = parsed_option
                except (json.JSONDecodeError, TypeError):
                    # 如果解析失败，保持原样
                    pass
        
        return attributes