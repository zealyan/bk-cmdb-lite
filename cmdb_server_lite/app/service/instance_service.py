from app.db.executor import query_all, query_one, execute
from app.db.engine import get_session
from app.utils.tools import generate_id
from datetime import datetime
import json

class InstanceService:
    
    @staticmethod
    def _get_table_name(model_id):
        """获取实例表名"""
        return f"cc_ObjectBase_0_pub_{model_id}"
    
    @staticmethod
    def get_instance(model_id, instance_id):
        """获取单个实例"""
        table_name = InstanceService._get_table_name(model_id)
        sql = f'SELECT * FROM "{table_name}" WHERE id = :instance_id'
        return query_one(sql, {'instance_id': instance_id})
    
    @staticmethod
    def get_instances(model_id, page=1, page_size=20, conditions=None):
        """获取模型实例列表（分页）"""
        table_name = InstanceService._get_table_name(model_id)
        offset = (page - 1) * page_size
        
        sql_parts = [f'SELECT * FROM "{table_name}"']
        params = {}
        
        if conditions and isinstance(conditions, dict):
            where_clauses = []
            for field, value in conditions.items():
                where_clauses.append(f'"{field}" = :{field}')
                params[field] = value
            if where_clauses:
                sql_parts.append('WHERE ' + ' AND '.join(where_clauses))
        
        sql_parts.append('ORDER BY id')
        sql_parts.append('LIMIT :limit OFFSET :offset')
        params['limit'] = page_size
        params['offset'] = offset
        
        sql = ' '.join(sql_parts)
        instances = query_all(sql, params)
        
        # 获取总数
        count_sql_parts = [f'SELECT COUNT(*) as total FROM "{table_name}"']
        if conditions and isinstance(conditions, dict):
            where_clauses = []
            for field, value in conditions.items():
                where_clauses.append(f'"{field}" = :{field}')
            if where_clauses:
                count_sql_parts.append('WHERE ' + ' AND '.join(where_clauses))
        
        count_sql = ' '.join(count_sql_parts)
        count_result = query_one(count_sql, params)
        total = count_result.get('total', 0) if count_result else 0
        
        return {
            'instances': instances,
            'page': page,
            'page_size': page_size,
            'total': total
        }
    
    @staticmethod
    def advanced_search(model_id, search_data):
        """高级搜索模型实例"""
        table_name = InstanceService._get_table_name(model_id)
        
        page = search_data.get('page', 1)
        page_size = search_data.get('page_size', 20)
        search = search_data.get('search')
        search_field = search_data.get('search_field')
        search_value = search_data.get('search_value')
        search_values = search_data.get('search_values')
        fuzzy = search_data.get('fuzzy', False)
        sort = search_data.get('sort')
        order = search_data.get('order', 'asc')
        operator = search_data.get('operator')
        conditions = search_data.get('conditions')
        search_start = search_data.get('search_start')
        search_end = search_data.get('search_end')
        
        offset = (page - 1) * page_size
        
        sql_parts = [f'SELECT * FROM "{table_name}"']
        params = {}
        
        where_clauses = []
        
        # 处理 conditions（多条件组合）
        if conditions and isinstance(conditions, list):
            for cond in conditions:
                if not isinstance(cond, dict):
                    continue
                
                field = cond.get('field', '')
                op = cond.get('operator', '$eq')
                value = cond.get('value', '')
                is_fuzzy = cond.get('fuzzy', False) or fuzzy
                
                # 映射前端操作符
                op_mapping = {
                    'contains': '$regex',
                    'equal': '$eq',
                    'not_equal': '$ne',
                    'in': '$in',
                    'not_in': '$nin',
                    'greater_than': '$gt',
                    'less_than': '$lt',
                    'greater_or_equal': '$gte',
                    'less_or_equal': '$lte'
                }
                if op in op_mapping:
                    op = op_mapping[op]
                
                if is_fuzzy:
                    op = '$regex'
                
                where_clause = InstanceService._build_condition(field, op, value)
                if where_clause:
                    where_clauses.append(where_clause)
        
        # 处理单条件搜索（兼容旧接口）
        elif search_field and (search_value or search_values or search_start or search_end):
            safe_field = search_field.strip()
            
            # 处理日期范围
            if search_start or search_end:
                if search_start:
                    safe_start = str(search_start).strip()
                    where_clauses.append(f'"{safe_field}" >= :search_start')
                    params['search_start'] = safe_start
                if search_end:
                    safe_end = str(search_end).strip()
                    where_clauses.append(f'"{safe_field}" <= :search_end')
                    params['search_end'] = safe_end
            else:
                # 处理普通搜索
                if search_values:
                    val_list = [str(v).strip() for v in search_values if v]
                elif search_value:
                    val_list = [search_value.strip()]
                else:
                    val_list = []
                
                if val_list:
                    if operator == '$ne':
                        if len(val_list) >= 1:
                            safe_val = val_list[0]
                            where_clauses.append(f'"{safe_field}" != :search_val')
                            params['search_val'] = safe_val
                    elif operator == '$nin':
                        placeholders = [f':search_val_{i}' for i in range(len(val_list))]
                        for i, val in enumerate(val_list):
                            params[f'search_val_{i}'] = val
                        where_clauses.append(f'"{safe_field}" NOT IN ({",".join(placeholders)})')
                    elif operator == '$in':
                        placeholders = [f':search_val_{i}' for i in range(len(val_list))]
                        for i, val in enumerate(val_list):
                            params[f'search_val_{i}'] = val
                        where_clauses.append(f'"{safe_field}" IN ({",".join(placeholders)})')
                    elif operator == '$gt':
                        safe_val = val_list[0]
                        where_clauses.append(f'"{safe_field}" > :search_val')
                        params['search_val'] = safe_val
                    elif operator == '$lt':
                        safe_val = val_list[0]
                        where_clauses.append(f'"{safe_field}" < :search_val')
                        params['search_val'] = safe_val
                    elif operator == '$gte':
                        safe_val = val_list[0]
                        where_clauses.append(f'"{safe_field}" >= :search_val')
                        params['search_val'] = safe_val
                    elif operator == '$lte':
                        safe_val = val_list[0]
                        where_clauses.append(f'"{safe_field}" <= :search_val')
                        params['search_val'] = safe_val
                    elif operator == '$like' or operator == '$regex' or fuzzy:
                        like_conditions = []
                        for i, val in enumerate(val_list):
                            param_name = f'search_val_{i}'
                            like_conditions.append(f'LOWER(CAST("{safe_field}" AS TEXT)) LIKE LOWER(:{param_name})')
                            params[param_name] = f'%{val}%'
                        if like_conditions:
                            where_clauses.append('(' + ' OR '.join(like_conditions) + ')')
                    else:
                        if len(val_list) == 1:
                            safe_val = val_list[0]
                            where_clauses.append(f'"{safe_field}" = :search_val')
                            params['search_val'] = safe_val
                        else:
                            placeholders = [f':search_val_{i}' for i in range(len(val_list))]
                            for i, val in enumerate(val_list):
                                params[f'search_val_{i}'] = val
                            where_clauses.append(f'"{safe_field}" IN ({",".join(placeholders)})')
        
        # 处理全局搜索
        elif search:
            # 获取模型的可搜索属性
            search_columns = InstanceService._get_search_columns(model_id)
            if search_columns:
                safe_search = search.strip()
                like_conditions = []
                for i, col in enumerate(search_columns):
                    param_name = f'search_col_{i}'
                    like_conditions.append(f'LOWER(CAST("{col}" AS TEXT)) LIKE LOWER(:{param_name})')
                    params[param_name] = f'%{safe_search}%'
                if like_conditions:
                    where_clauses.append('(' + ' OR '.join(like_conditions) + ')')
        
        if where_clauses:
            sql_parts.append('WHERE ' + ' AND '.join(where_clauses))
        
        # 处理排序
        sort_clause = ''
        if sort:
            sort_str = str(sort).strip()
            if sort_str.startswith('-'):
                sort_field = sort_str[1:]
                sort_dir = 'DESC'
            else:
                sort_field = sort_str
                sort_dir = order.upper() if order else 'ASC'
            
            if sort_field.replace('_', '').replace('-', '').isalnum():
                sort_clause = f' ORDER BY "{sort_field}" {sort_dir}'
        else:
            sort_clause = ' ORDER BY id'
        
        sql_parts.append(sort_clause)
        sql_parts.append(f' LIMIT :limit OFFSET :offset')
        params['limit'] = page_size
        params['offset'] = offset
        
        sql = ''.join(sql_parts)
        instances = query_all(sql, params)
        
        # 获取总数
        count_sql_parts = [f'SELECT COUNT(*) as total FROM "{table_name}"']
        if where_clauses:
            count_sql_parts.append(' WHERE ' + ' AND '.join(where_clauses))
        
        count_sql = ''.join(count_sql_parts)
        count_result = query_one(count_sql, params)
        total = count_result.get('total', 0) if count_result else 0
        
        return {
            'instances': instances,
            'page': page,
            'page_size': page_size,
            'total': total
        }
    
    @staticmethod
    def _build_condition(field, op, value):
        """构建单个条件"""
        safe_field = field.strip()
        if not safe_field.replace('_', '').replace('-', '').isalnum():
            return None
        
        # 解析多个值
        if isinstance(value, list):
            val_list = [str(v).strip() for v in value if v]
        elif isinstance(value, str):
            val_list = [v.strip() for v in value.split(',') if v.strip()]
        else:
            val_list = [str(value).strip()]
        
        if not val_list:
            return None
        
        # 根据操作符构建条件
        if op == '$ne':
            if len(val_list) >= 1:
                safe_val = val_list[0]
                return f'"{safe_field}" != "{safe_val}"'
        elif op == '$nin':
            in_vals = '", "'.join([v.replace('"', '""') for v in val_list])
            return f'"{safe_field}" NOT IN ("{in_vals}")'
        elif op == '$in':
            in_vals = '", "'.join([v.replace('"', '""') for v in val_list])
            return f'"{safe_field}" IN ("{in_vals}")'
        elif op == '$gt':
            safe_val = val_list[0]
            return f'"{safe_field}" > "{safe_val}"'
        elif op == '$lt':
            safe_val = val_list[0]
            return f'"{safe_field}" < "{safe_val}"'
        elif op == '$gte':
            safe_val = val_list[0]
            return f'"{safe_field}" >= "{safe_val}"'
        elif op == '$lte':
            safe_val = val_list[0]
            return f'"{safe_field}" <= "{safe_val}"'
        elif op == '$like' or op == '$regex':
            like_parts = [f'LOWER(CAST("{safe_field}" AS TEXT)) LIKE LOWER("%{v.replace("%", "%%").replace("_", "%%_")}%")' 
                         for v in val_list]
            return '(' + ' OR '.join(like_parts) + ')'
        else:
            if len(val_list) == 1:
                safe_val = val_list[0]
                return f'"{safe_field}" = "{safe_val}"'
            else:
                in_vals = '", "'.join([v.replace('"', '""') for v in val_list])
                return f'"{safe_field}" IN ("{in_vals}")'
        
        return None
    
    @staticmethod
    def _get_search_columns(model_id):
        """获取模型的可搜索属性列表"""
        from app.service.model_service import ModelService
        attributes = ModelService.get_model_attributes(model_id)
        
        # 选择前几个属性作为搜索字段
        search_columns = []
        for attr in attributes:
            prop_id = attr.get('bk_property_id')
            if prop_id and prop_id not in ['id', '_id', 'create_time', 'last_time', 'bk_supplier_account']:
                search_columns.append(prop_id)
                if len(search_columns) >= 8:
                    break
        
        if not search_columns:
            search_columns = ['id']
        
        return search_columns
    
    @staticmethod
    def count_instances(model_id):
        """统计模型实例数量"""
        table_name = InstanceService._get_table_name(model_id)
        sql = f'SELECT COUNT(*) as total FROM "{table_name}"'
        result = query_one(sql, {})
        return result.get('total', 0) if result else 0
    
    @staticmethod
    def create_instance(model_id, data):
        """创建实例"""
        table_name = InstanceService._get_table_name(model_id)
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        instance_id = generate_id()
        data['id'] = instance_id
        data['_id'] = instance_id
        data.setdefault('bk_supplier_account', '0')
        data.setdefault('create_time', now)
        data.setdefault('last_time', now)
        
        # 清理字段，只保留安全字段
        from app.service.model_service import ModelService
        attributes = ModelService.get_model_attributes(model_id)
        valid_fields = set([attr.get('bk_property_id') for attr in attributes])
        valid_fields.update(SYSTEM_FIELDS)
        
        clean_data = {}
        for key, value in data.items():
            if key in valid_fields:
                # 处理JSON类型的字段
                if isinstance(value, (dict, list)):
                    clean_data[key] = json.dumps(value)
                elif value is None:
                    clean_data[key] = None
                else:
                    clean_data[key] = str(value) if not isinstance(value, (int, float)) else value
        
        if not clean_data:
            raise ValueError('No valid data to insert')
        
        columns = list(clean_data.keys())
        placeholders = [f':{col}' for col in columns]
        
        sql = f'INSERT INTO "{table_name}" ({",".join([f"{col}" for col in columns])}) VALUES ({",".join(placeholders)})'
        execute(sql, clean_data)
        
        return InstanceService.get_instance(model_id, instance_id)
    
    @staticmethod
    def update_instance(model_id, instance_id, data):
        """更新实例"""
        table_name = InstanceService._get_table_name(model_id)
        
        data['last_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取有效字段
        from app.service.model_service import ModelService
        attributes = ModelService.get_model_attributes(model_id)
        valid_fields = set([attr.get('bk_property_id') for attr in attributes])
        valid_fields.update(SYSTEM_FIELDS)
        # 不允许修改系统字段
        system_fields_to_exclude = ['id', '_id', 'bk_supplier_account', 'create_time']
        
        update_fields = []
        params = {'instance_id': instance_id}
        
        for key, value in data.items():
            if key in valid_fields and key not in system_fields_to_exclude:
                update_fields.append(f'"{key}" = :{key}')
                if isinstance(value, (dict, list)):
                    params[key] = json.dumps(value)
                elif value is None:
                    params[key] = None
                else:
                    params[key] = str(value) if not isinstance(value, (int, float)) else value
        
        if not update_fields:
            return InstanceService.get_instance(model_id, instance_id)
        
        sql = f'UPDATE "{table_name}" SET {",".join(update_fields)} WHERE id = :instance_id'
        execute(sql, params)
        
        return InstanceService.get_instance(model_id, instance_id)
    
    @staticmethod
    def batch_update_instances(model_id, ids, data):
        """批量更新实例"""
        if not ids:
            return 0
        
        table_name = InstanceService._get_table_name(model_id)
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data['last_time'] = now
        
        # 获取有效字段
        from app.service.model_service import ModelService
        attributes = ModelService.get_model_attributes(model_id)
        valid_fields = set([attr.get('bk_property_id') for attr in attributes])
        valid_fields.update(SYSTEM_FIELDS)
        # 不允许修改系统字段
        system_fields_to_exclude = ['id', '_id', 'bk_supplier_account', 'create_time']
        
        update_fields = []
        params = {}
        param_idx = 0
        
        for key, value in data.items():
            if key in valid_fields and key not in system_fields_to_exclude:
                param_name = f'val_{param_idx}'
                update_fields.append(f'"{key}" = :{param_name}')
                if isinstance(value, (dict, list)):
                    params[param_name] = json.dumps(value)
                elif value is None:
                    params[param_name] = None
                else:
                    params[param_name] = str(value) if not isinstance(value, (int, float)) else value
                param_idx += 1
        
        if not update_fields:
            return len(ids)
        
        # 构建IN子句的参数
        id_params = []
        for idx, inst_id in enumerate(ids):
            param_name = f'id_{idx}'
            id_params.append(f':{param_name}')
            params[param_name] = inst_id
        
        sql = f'UPDATE "{table_name}" SET {",".join(update_fields)} WHERE id IN ({",".join(id_params)})'
        execute(sql, params)
        
        return len(ids)
    
    @staticmethod
    def delete_instances(model_id, ids):
        """删除实例（支持批量）"""
        table_name = InstanceService._get_table_name(model_id)
        
        if not ids:
            return 0
        
        # 先删除关联表中的记录
        placeholders = ','.join(['?' for _ in ids])
        
        delete_assoc_src_sql = f'DELETE FROM cc_InstAsst_0_pub WHERE bk_obj_id = ? AND bk_inst_id IN ({placeholders})'
        execute(delete_assoc_src_sql, [model_id] + ids)
        
        delete_assoc_dest_sql = f'DELETE FROM cc_InstAsst_0_pub WHERE bk_asst_obj_id = ? AND bk_asst_inst_id IN ({placeholders})'
        execute(delete_assoc_dest_sql, [model_id] + ids)
        
        # 删除实例表中的记录
        delete_instance_sql = f'DELETE FROM "{table_name}" WHERE id IN ({placeholders})'
        execute(delete_instance_sql, ids)
        
        return len(ids)


# 系统字段列表
SYSTEM_FIELDS = {
    '_id', 
    'id', 
    'bk_inst_id', 
    'bk_inst_name', 
    'bk_obj_id', 
    'bk_supplier_account', 
    'create_time', 
    'last_time', 
    'bk_operate_time',
    'bk_created_by',
    'bk_created_at',
    'bk_updated_by',
    'bk_updated_at',
    'modifier'
}
