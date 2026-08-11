from app.db.executor import query_all, query_one, execute
from app.definitions import PROPERTY_TYPE_BOOL
from app.utils.tools import generate_group_id
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
                if prop_type == PROPERTY_TYPE_BOOL:
                    attr['option'] = False
                continue

            if prop_type == PROPERTY_TYPE_BOOL:
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
    def create_model_property_group(model_id, bk_group_name, bk_group_index=99, is_collapse=False):
        """新建属性分组。

        对齐上游 bk-cmdb：分组 ID（bk_group_id）由系统随机生成（generate_group_id，
        非顺序、非小写标识符约束），显示名（bk_group_name）由调用方提供。
        同名分组（同模型内）视为冲突，直接报错。

        :returns: 新建的分组整行
        :raises ValueError: 显示名为空 / 同名分组已存在 / 模型不存在
        """
        if not bk_group_name or not str(bk_group_name).strip():
            raise ValueError('分组显示名 bk_group_name 不能为空')
        bk_group_name = str(bk_group_name).strip()

        if not query_one("SELECT 1 FROM cc_ObjDes WHERE bk_obj_id = :o", {'o': model_id}):
            raise ValueError(f'模型不存在: {model_id}')

        dup = query_one(
            "SELECT 1 FROM cc_PropertyGroup WHERE bk_obj_id = :o AND bk_group_name = :n",
            {'o': model_id, 'n': bk_group_name})
        if dup:
            raise ValueError(f'分组显示名已存在: {bk_group_name}')

        bk_group_id = generate_group_id()
        execute(
            "INSERT INTO cc_PropertyGroup "
            "(_id, bk_obj_id, bk_group_id, bk_group_name, bk_group_index, "
            "bk_isdefault, is_collapse, ispre, bk_biz_id, bk_supplier_account, "
            "creator, modifier) VALUES "
            "(:_id, :bk_obj_id, :bk_group_id, :bk_group_name, :bk_group_index, "
            "false, :is_collapse, true, 0, '0', 'admin', 'admin')",
            {
                '_id': f"{model_id}.{bk_group_id}",
                'bk_obj_id': model_id,
                'bk_group_id': bk_group_id,
                'bk_group_name': bk_group_name,
                'bk_group_index': int(bk_group_index),
                'is_collapse': bool(is_collapse),
            })
        return query_one(
            "SELECT * FROM cc_PropertyGroup WHERE bk_obj_id = :o AND bk_group_id = :g",
            {'o': model_id, 'g': bk_group_id})

    @staticmethod
    def update_model_property_group(model_id, group_id, bk_group_name=None,
                                     bk_group_index=None, is_collapse=None):
        """修改属性分组（显示名 / 排序 / 折叠）。

        :returns: 更新后的分组整行
        :raises ValueError: 分组不存在 / 改名后与其他分组同名
        """
        existing = query_one(
            "SELECT * FROM cc_PropertyGroup WHERE bk_obj_id = :o AND bk_group_id = :g",
            {'o': model_id, 'g': group_id})
        if not existing:
            raise ValueError(f'分组不存在: {group_id}')

        if bk_group_name is not None and str(bk_group_name).strip() \
                and str(bk_group_name).strip() != existing.get('bk_group_name'):
            new_name = str(bk_group_name).strip()
            dup = query_one(
                "SELECT 1 FROM cc_PropertyGroup "
                "WHERE bk_obj_id = :o AND bk_group_name = :n AND bk_group_id != :g",
                {'o': model_id, 'n': new_name, 'g': group_id})
            if dup:
                raise ValueError(f'分组显示名已存在: {new_name}')
            existing['bk_group_name'] = new_name

        if bk_group_index is not None:
            existing['bk_group_index'] = int(bk_group_index)
        if is_collapse is not None:
            existing['is_collapse'] = bool(is_collapse)

        execute(
            "UPDATE cc_PropertyGroup SET bk_group_name = :n, bk_group_index = :i, "
            "is_collapse = :c, modifier = 'admin', last_time = CURRENT_TIMESTAMP "
            "WHERE bk_obj_id = :o AND bk_group_id = :g",
            {
                'n': existing['bk_group_name'],
                'i': existing['bk_group_index'],
                'c': existing['is_collapse'],
                'o': model_id,
                'g': group_id,
            })
        return query_one(
            "SELECT * FROM cc_PropertyGroup WHERE bk_obj_id = :o AND bk_group_id = :g",
            {'o': model_id, 'g': group_id})

    @staticmethod
    def delete_model_property_group(model_id, group_id):
        """删除属性分组。

        默认分组（default）禁止删除；被删分组下的属性回落到 default，
        与上游 DeleteObjectAttributeGroup 行为一致。

        :returns: 被删分组的 bk_group_id
        :raises ValueError: 默认分组不可删 / 分组不存在
        """
        if group_id == 'default':
            raise ValueError('默认分组不可删除')
        existing = query_one(
            "SELECT 1 FROM cc_PropertyGroup WHERE bk_obj_id = :o AND bk_group_id = :g",
            {'o': model_id, 'g': group_id})
        if not existing:
            raise ValueError(f'分组不存在: {group_id}')

        execute(
            "UPDATE cc_ObjAttDes SET bk_property_group = 'default' "
            "WHERE bk_obj_id = :o AND bk_property_group = :g",
            {'o': model_id, 'g': group_id})
        execute(
            "DELETE FROM cc_PropertyGroup WHERE bk_obj_id = :o AND bk_group_id = :g",
            {'o': model_id, 'g': group_id})
        return group_id
    
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
    def update_model(model_id, data):
        """更新模型元数据（如 bk_ispaused 停用/启用）

        Args:
            model_id: 模型 ID（bk_obj_id）
            data: 需更新的字段字典，目前支持 bk_ispaused

        Returns:
            更新后的模型对象，若模型不存在则返回 None
        """
        model = ModelService.get_model_by_id(model_id)
        if not model:
            return None

        allowed_fields = {'bk_ispaused'}
        update_data = {}
        for key, value in data.items():
            if key in allowed_fields:
                # SQLite boolean → 0/1
                update_data[key] = 1 if value else 0

        if update_data:
            execute(
                'UPDATE cc_ObjDes SET bk_ispaused = :bk_ispaused WHERE bk_obj_id = :model_id',
                {'bk_ispaused': update_data.get('bk_ispaused', 0), 'model_id': model_id}
            )

        return ModelService.get_model_by_id(model_id)

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