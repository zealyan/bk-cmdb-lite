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

        # 处理布尔值字段和 option 字段
        boolean_fields = [
            'bk_isapi', 'bk_issystem', 'bk_ishidden', 'bk_ispassword',
            'isrequired', 'isreadonly', 'editable', 'ispre', 'ismultiple'
        ]

        for attr in attributes:
            # 转换布尔字段
            for field in boolean_fields:
                if field in attr and attr[field] is not None:
                    if isinstance(attr[field], int):
                        attr[field] = bool(attr[field])

            # 处理 option 字段的反序列化
            prop_type = attr.get('bk_property_type', '')
            option = attr.get('option')

            if option is None or option == '':
                # bool 类型的 option 默认为 false（作为默认值）
                if prop_type == 'bool':
                    attr['option'] = False
                continue

            if prop_type == 'bool':
                # bool 类型的 option 是布尔值本身（可能存储为字符串 'true'/'false'）
                if isinstance(option, bool):
                    attr['option'] = option
                elif isinstance(option, str):
                    attr['option'] = option.lower() == 'true'
                elif isinstance(option, int):
                    attr['option'] = bool(option)
                else:
                    attr['option'] = False
            else:
                # 其他类型按 JSON 解析
                try:
                    parsed_option = json.loads(option)
                    attr['option'] = parsed_option
                except (json.JSONDecodeError, TypeError):
                    pass

        return attributes
    
    @staticmethod
    def get_model_property_groups(model_id):
        """获取模型的属性分组"""
        return query_all('model/select_property_groups.sql', {
            'model_id': model_id
        })