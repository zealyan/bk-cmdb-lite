from app.db.executor import query_all, query_one
import json

DEFAULT_OBJ_ICON = 'icon-cc-default'

class ModelService:
    
    @staticmethod
    def get_all_models():
        """获取所有模型"""
        models = query_all('model/select_models.sql', {})
        for model in models:
            if not model.get('bk_obj_icon'):
                model['bk_obj_icon'] = DEFAULT_OBJ_ICON
        return models
    
    @staticmethod
    def get_model_by_id(model_id):
        """获取模型详情"""
        model = query_one('model/select_model_by_id.sql', {
            'model_id': model_id
        })
        if model and not model.get('bk_obj_icon'):
            model['bk_obj_icon'] = DEFAULT_OBJ_ICON
        return model
    
    @staticmethod
    def get_model_attributes(model_id, for_web=False):
        """获取模型属性

        与原项目规则保持一致:
        - for_web=False: 返回全部属性（后端内部使用，如验证、唯一性检查、类型映射）
        - for_web=True: 过滤掉 bk_issystem=true 和 bk_isapi=true 的系统字段，
          仅返回前端可见的属性。参考原项目 SearchObjectAttributeForWeb:
          /workspace/bk-cmdb/src/scene_server/topo_server/service/object_attribute.go
          中 combinationSearchObjectAttrCond 函数强制设置查询条件:
            bk_issystem = false
            bk_isapi = false
        """
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

        # for_web=True 时，过滤掉系统字段和 API 字段（与原项目后端过滤规则一致）
        # 原项目在 combinationSearchObjectAttrCond 中强制设置:
        #   bk_issystem = false  → 过滤 bk_obj_id 等系统内部字段
        #   bk_isapi = false     → 过滤 id、bk_inst_id 等 API 字段
        # 这些字段不应返回给前端展示
        if for_web:
            attributes = [
                attr for attr in attributes
                if not attr.get('bk_issystem', False) and not attr.get('bk_isapi', False)
            ]

        return attributes
    
    @staticmethod
    def get_model_property_groups(model_id):
        """获取模型的属性分组"""
        return query_all('model/select_property_groups.sql', {
            'model_id': model_id
        })
    
    @staticmethod
    def get_object_unique(model_id):
        """获取模型的唯一约束"""
        results = query_all("""
            SELECT id, bk_obj_id, keys, ispre, bk_supplier_account, last_time
            FROM cc_ObjectUnique 
            WHERE bk_obj_id = :model_id AND bk_supplier_account = '0'
        """, {'model_id': model_id})
        
        for result in results:
            keys = result.get('keys')
            if keys:
                try:
                    result['keys'] = json.loads(keys)
                except (json.JSONDecodeError, TypeError):
                    result['keys'] = []
        return results
    
    @staticmethod
    def create_object_unique(model_id, keys):
        """创建模型的唯一约束"""
        keys_json = json.dumps(keys)
        
        result = query_one("""
            INSERT INTO cc_ObjectUnique (bk_obj_id, keys, ispre, bk_supplier_account)
            VALUES (:bk_obj_id, :keys, :ispre, '0')
            RETURNING id
        """, {
            'bk_obj_id': model_id,
            'keys': keys_json,
            'ispre': False
        })
        
        return result.get('id') if result else None
    
    @staticmethod
    def update_object_unique(model_id, unique_id, keys):
        """更新模型的唯一约束"""
        keys_json = json.dumps(keys)
        
        result = query_one("""
            UPDATE cc_ObjectUnique 
            SET keys = :keys, last_time = CURRENT_TIMESTAMP
            WHERE id = :id AND bk_obj_id = :bk_obj_id AND bk_supplier_account = '0'
            RETURNING id
        """, {
            'id': unique_id,
            'bk_obj_id': model_id,
            'keys': keys_json
        })
        
        return result is not None
    
    @staticmethod
    def delete_object_unique(model_id, unique_id):
        """删除模型的唯一约束"""
        result = query_one("""
            DELETE FROM cc_ObjectUnique 
            WHERE id = :id AND bk_obj_id = :bk_obj_id AND bk_supplier_account = '0'
            RETURNING id
        """, {
            'id': unique_id,
            'bk_obj_id': model_id
        })
        
        return result is not None