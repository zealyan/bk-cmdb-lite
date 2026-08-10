from app.db.executor import query_all, query_one, execute
from app.db.engine import get_session, get_engine
from app.utils.tools import generate_id
from app.utils.exceptions import ValidationException
from app.definitions import (
    PROPERTY_TYPE_BOOL,
    PROPERTY_TYPE_INT,
    PROPERTY_TYPE_LIST,
    NUMERIC_PROPERTY_TYPES,
    OBJUSER_PROPERTY_TYPES,
    JSON_VALUE_PROPERTY_TYPES,
    ASSOCIATION_PROPERTY_TYPES,
)
from sqlalchemy import inspect
from datetime import datetime
import json


# 表真实列名缓存（SQLAlchemy 反射，数据库无关；SQLite/PostgreSQL/MySQL 通用）
_table_columns_cache = {}


def get_table_columns(table_name):
    """获取目标表的真实列名集合；带缓存，避免每次写入都反射。"""
    if table_name not in _table_columns_cache:
        try:
            cols = inspect(get_engine()).get_columns(table_name)
            _table_columns_cache[table_name] = {c['name'] for c in cols}
        except Exception:
            # 反射失败（如表尚未创建）时返回空集合，由后续 SQL 执行暴露真实错误
            _table_columns_cache[table_name] = set()
    return _table_columns_cache[table_name]

class InstanceService:
    
    # 内置模型表名映射（与蓝鲸CMDB原项目保持一致）
    BUILTIN_TABLE_MAP = {
        'biz': 'cc_ApplicationBase',
        'set': 'cc_SetBase',
        'module': 'cc_ModuleBase',
        'host': 'cc_HostBase',
        'bk_host': 'cc_HostBase'
    }
    
    # 内置模型主键字段映射
    BUILTIN_ID_FIELD_MAP = {
        'biz': 'bk_biz_id',
        'set': 'bk_set_id',
        'module': 'bk_module_id',
        'host': 'bk_host_id',
        'bk_host': 'bk_host_id'
    }

    @staticmethod
    def list_models():
        """获取所有模型列表"""
        return query_all("SELECT * FROM cc_ObjDes ORDER BY obj_sort_number")
    
    @staticmethod
    def _get_table_name(model_id):
        """获取实例表名（内置模型使用专用表，自定义模型使用 ObjectBase 分表）"""
        # 检查是否为内置模型
        if model_id in InstanceService.BUILTIN_TABLE_MAP:
            return InstanceService.BUILTIN_TABLE_MAP[model_id]
        # 自定义模型使用 ObjectBase 分表
        return f"cc_ObjectBase_0_pub_{model_id}"
    
    @staticmethod
    def _get_id_field(model_id):
        """获取模型的主键字段名"""
        if model_id in InstanceService.BUILTIN_ID_FIELD_MAP:
            return InstanceService.BUILTIN_ID_FIELD_MAP[model_id]
        return 'bk_inst_id'
    
    @staticmethod
    def get_instance(model_id, instance_id):
        """获取单个实例"""
        table_name = InstanceService._get_table_name(model_id)
        id_field = InstanceService._get_id_field(model_id)
        sql = f'SELECT * FROM "{table_name}" WHERE "{id_field}" = :instance_id'
        instance = query_one(sql, {'instance_id': instance_id})
        if instance:
            instance = InstanceService._parse_json_fields(instance, model_id)
        return instance
    
    @staticmethod
    def get_instances(model_id, page=1, page_size=20, conditions=None):
        """获取模型实例列表（分页）"""
        table_name = InstanceService._get_table_name(model_id)
        id_field = InstanceService._get_id_field(model_id)
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
        
        sql_parts.append(f'ORDER BY "{id_field}"')
        sql_parts.append('LIMIT :limit OFFSET :offset')
        params['limit'] = page_size
        params['offset'] = offset
        
        sql = ' '.join(sql_parts)
        instances = query_all(sql, params)
        
        # 解析JSON字段
        for i in range(len(instances)):
            instances[i] = InstanceService._parse_json_fields(instances[i], model_id)
        
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
    def get_instances_by_ids(model_id, instance_ids):
        """按实例ID列表批量查询实例"""
        table_name = InstanceService._get_table_name(model_id)
        id_field = InstanceService._get_id_field(model_id)
        
        if not instance_ids:
            return []
        
        placeholders = ','.join([':id_' + str(i) for i in range(len(instance_ids))])
        params = {'id_' + str(i): int(instance_ids[i]) for i in range(len(instance_ids))}
        
        sql = f'SELECT * FROM "{table_name}" WHERE "{id_field}" IN ({placeholders})'
        instances = query_all(sql, params)
        
        for i in range(len(instances)):
            instances[i] = InstanceService._parse_json_fields(instances[i], model_id)
        
        return instances
    
    @staticmethod
    def advanced_search(model_id, search_data):
        """高级搜索模型实例"""
        from app.utils.logger import get_logger
        logger = get_logger('api.instance')
        
        logger.info(f'[advanced_search] model_id={model_id}, search_data={search_data}')
        
        table_name = InstanceService._get_table_name(model_id)
        
        # 处理 page 参数，支持字典和整数两种格式
        page_param = search_data.get('page')
        if isinstance(page_param, dict):
            page_size = page_param.get('limit', 20)
            offset = page_param.get('start', 0)
            page = offset // page_size + 1 if page_size > 0 else 1
        else:
            page = int(page_param) if page_param else 1
            page_size = search_data.get('page_size', 20)
            offset = (page - 1) * page_size
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
        
        logger.info(f'[advanced_search] conditions={conditions}, search_field={search_field}')

        from app.service.model_service import ModelService
        attributes = ModelService.get_model_attributes(model_id)
        attr_type_map = {}
        for attr in attributes:
            pid = attr.get('bk_property_id')
            if pid:
                attr_type_map[pid] = attr.get('bk_property_type', '')
        
        sql_parts = [f'SELECT * FROM "{table_name}"']
        params = {}
        
        where_clauses = []
        
        # 处理 conditions（多条件组合）
        # 支持两种格式：
        # 1. 列表格式：[{"field": "...", "operator": "...", "value": "..."}]
        # 2. 对象格式：{"condition": "AND", "rules": [...]}
        param_counter = 0
        if conditions:
            rule_list = []
            
            if isinstance(conditions, list):
                # 列表格式
                rule_list = conditions
            elif isinstance(conditions, dict):
                # 对象格式，提取 rules
                rule_list = conditions.get('rules', [])
            
            for cond in rule_list:
                if not isinstance(cond, dict):
                    continue
                
                field = cond.get('field', '')
                op = cond.get('operator', '$eq')
                value = cond.get('value', '')
                is_fuzzy = cond.get('fuzzy', False) or fuzzy

                field_type = attr_type_map.get(field, '')
                if field_type == PROPERTY_TYPE_BOOL:
                    value = InstanceService._parse_bool_value_for_search(value)

                # 映射前端操作符（语义操作符 → MongoDB 风格操作符）
                op_mapping = {
                    'contains': '$regex',
                    'equal': '$eq',
                    'not_equal': '$ne',
                    'in': '$in',
                    'not_in': '$nin',
                    'greater_than': '$gt',
                    'less_than': '$lt',
                    'greater_or_equal': '$gte',
                    'less_or_equal': '$lte',
                    'between': '$range',
                    'not_between': '$nrange',
                    'datetime_greater_or_equal': '$gte',
                    'datetime_less_or_equal': '$lte',
                    'datetime_greater_than': '$gt',
                    'datetime_less_than': '$lt'
                }
                if op in op_mapping:
                    op = op_mapping[op]
                
                if is_fuzzy:
                    op = '$regex'
                
                field_type = attr_type_map.get(field, '')
                where_clause, param_counter = InstanceService._build_condition(field, op, value, params, param_counter, field_type)
                if where_clause:
                    where_clauses.append(where_clause)
        
        # 处理单条件搜索（兼容旧接口）
        elif search_field and (search_value or search_values or search_start or search_end):
            safe_field = search_field.strip()
            is_bool_field = attr_type_map.get(safe_field, '') == PROPERTY_TYPE_BOOL

            # 处理日期范围
            if search_start or search_end:
                field_type = attr_type_map.get(safe_field, '')
                is_numeric = field_type in NUMERIC_PROPERTY_TYPES
                if search_start:
                    if is_numeric:
                        try:
                            if field_type == PROPERTY_TYPE_INT:
                                params['search_start'] = int(search_start)
                            else:
                                params['search_start'] = float(search_start)
                        except (ValueError, TypeError):
                            params['search_start'] = str(search_start).strip()
                    else:
                        params['search_start'] = str(search_start).strip()
                    where_clauses.append(f'"{safe_field}" >= :search_start')
                if search_end:
                    if is_numeric:
                        try:
                            if field_type == PROPERTY_TYPE_INT:
                                params['search_end'] = int(search_end)
                            else:
                                params['search_end'] = float(search_end)
                        except (ValueError, TypeError):
                            params['search_end'] = str(search_end).strip()
                    else:
                        params['search_end'] = str(search_end).strip()
                    where_clauses.append(f'"{safe_field}" <= :search_end')
            else:
                # 处理普通搜索
                field_type = attr_type_map.get(safe_field, '')
                is_numeric_field = field_type in NUMERIC_PROPERTY_TYPES
                if search_values:
                    # 兼容字符串（逗号分隔）和列表两种输入形式
                    if isinstance(search_values, str):
                        raw_values = [v.strip() for v in search_values.split(',') if v and v.strip()]
                    else:
                        raw_values = list(search_values)
                    if is_bool_field:
                        val_list = []
                        for v in raw_values:
                            if v is None or v == '':
                                continue
                            parsed_val = InstanceService._parse_bool_value_for_search(v)
                            if parsed_val is not None:
                                val_list.append(parsed_val)
                    elif is_numeric_field:
                        val_list = []
                        for v in raw_values:
                            if v is None or v == '':
                                continue
                            try:
                                if field_type == PROPERTY_TYPE_INT:
                                    val_list.append(int(v))
                                else:
                                    val_list.append(float(v))
                            except (ValueError, TypeError):
                                val_list.append(str(v).strip())
                    else:
                        val_list = [str(v).strip() for v in raw_values if v]
                elif search_value:
                    if is_bool_field:
                        parsed = InstanceService._parse_bool_value_for_search(search_value)
                        val_list = [parsed] if parsed is not None else []
                    elif is_numeric_field:
                        try:
                            if field_type == PROPERTY_TYPE_INT:
                                val_list = [int(search_value)]
                            else:
                                val_list = [float(search_value)]
                        except (ValueError, TypeError):
                            val_list = [str(search_value).strip()]
                    else:
                        val_list = [str(search_value).strip()]
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
            id_field = InstanceService._get_id_field(model_id)
            sort_clause = f' ORDER BY "{id_field}"'
        
        sql_parts.append(sort_clause)
        sql_parts.append(f' LIMIT :limit OFFSET :offset')
        params['limit'] = page_size
        params['offset'] = offset
        
        sql = ''.join(sql_parts)
        instances = query_all(sql, params)
        
        # 解析JSON字段
        for i in range(len(instances)):
            instances[i] = InstanceService._parse_json_fields(instances[i], model_id)
        
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
    def _parse_json_fields(instance, model_id):
        """解析JSON字段，将enum等类型的JSON字符串解析为数组或对象"""
        from app.service.model_service import ModelService

        if not instance:
            return instance

        # 保留 id 字段：数据库内部主键 id 用于关联匹配
        # 前端 instance-association 组件使用 inst.id 来匹配关联记录中的 bk_inst_id/bk_asst_inst_id
        # 同时也保留 bk_inst_id 作为蓝鲸标准实例ID字段
        if '_id' in instance:
            del instance['_id']

        # 获取模型的所有属性，确定哪些是需要解析JSON的字段
        attributes = ModelService.get_model_attributes(model_id)

        for attr in attributes:
            prop_id = attr.get('bk_property_id')
            prop_type = attr.get('bk_property_type')

            # 关联类型（singleasst/multiasst/foreignkey）：不落实例表列，
            # 关联数据存于 cc_InstAsst，跳过不解析。
            if prop_type in ASSOCIATION_PROPERTY_TYPES:
                continue

            if prop_id and prop_id in instance:
                value = instance[prop_id]

                # bool 类型：SQLite可能存储为 0/1 或 'true'/'false' 字符串
                if prop_type == PROPERTY_TYPE_BOOL:
                    if value is None:
                        instance[prop_id] = False
                    elif isinstance(value, bool):
                        instance[prop_id] = value
                    elif isinstance(value, int):
                        instance[prop_id] = bool(value)
                    elif isinstance(value, str):
                        val_lower = value.lower().strip()
                        if val_lower in ('true', '1', 'yes', 'on'):
                            instance[prop_id] = True
                        elif val_lower in ('false', '0', 'no', 'off', ''):
                            instance[prop_id] = False
                        else:
                            instance[prop_id] = bool(value)
                    else:
                        instance[prop_id] = bool(value)
                    continue

                # objuser（MongoDB 为纯逗号拼接字符串）：落库即纯字符串，读取原样返回，不做 JSON 解析
                if prop_type in OBJUSER_PROPERTY_TYPES:
                    continue

                # organization（MongoDB 为部门 ID 数组）：落库为 JSON 文本，读取解析回数组
                if prop_type in JSON_VALUE_PROPERTY_TYPES:
                    if value is not None and isinstance(value, str):
                        try:
                            instance[prop_id] = json.loads(value)
                        except (json.JSONDecodeError, ValueError):
                            pass
                    continue

                # 其他类型：按 JSON 解析
                if value is not None and isinstance(value, str) and value.strip().startswith(('[', '{')):
                    try:
                        parsed = json.loads(value)
                        instance[prop_id] = parsed

                        # 对于list类型，如果解包是双重编码，则再解一次
                        if prop_type == PROPERTY_TYPE_LIST and isinstance(parsed, str) and parsed.strip().startswith(('[', '{')):
                            try:
                                instance[prop_id] = json.loads(parsed)
                            except (json.JSONDecodeError, ValueError):
                                pass
                    except (json.JSONDecodeError, ValueError):
                        # 如果解析失败，保持原样
                        pass

        return instance

    @staticmethod
    def _parse_bool_value_for_search(value):
        """将各种形式的 bool 值转换为整数 1/0（与数据库存储一致）"""
        if value is None or value == '':
            return None
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, int):
            return 1 if value else 0
        if isinstance(value, float):
            return 1 if value else 0
        if isinstance(value, str):
            v_lower = value.strip().lower()
            if v_lower in ('true', '1', 'yes', 'on', 't'):
                return 1
            elif v_lower in ('false', '0', 'no', 'off', 'f', ''):
                return 0
            return None
        return 1 if bool(value) else 0

    @staticmethod
    def _build_condition(field, op, value, params, param_counter, field_type=''):
        """构建单个条件（使用参数化查询）"""
        safe_field = field.strip()
        if not safe_field.replace('_', '').replace('-', '').isalnum():
            return None, param_counter

        numeric_types = NUMERIC_PROPERTY_TYPES
        is_numeric = field_type in numeric_types

        # 解析多个值。如果值已经是整数/布尔类型，保持原样（避免 bool 的 1/0 被转成字符串）
        if isinstance(value, list):
            val_list = []
            for v in value:
                if v is None or (isinstance(v, str) and v.strip() == ''):
                    continue
                if isinstance(v, bool):
                    val_list.append(1 if v else 0)
                elif isinstance(v, (int, float)):
                    val_list.append(v)
                elif is_numeric:
                    try:
                        if field_type == PROPERTY_TYPE_INT:
                            val_list.append(int(v))
                        else:
                            val_list.append(float(v))
                    except (ValueError, TypeError):
                        val_list.append(str(v).strip())
                else:
                    val_list.append(str(v).strip())
        elif isinstance(value, bool):
            val_list = [1 if value else 0]
        elif isinstance(value, (int, float)):
            val_list = [value]
        elif isinstance(value, str):
            raw_values = [v.strip() for v in value.split(',') if v.strip()]
            if is_numeric:
                val_list = []
                for v in raw_values:
                    try:
                        if field_type == PROPERTY_TYPE_INT:
                            val_list.append(int(v))
                        else:
                            val_list.append(float(v))
                    except (ValueError, TypeError):
                        val_list.append(v)
            else:
                val_list = raw_values
        else:
            val_list = [str(value).strip()]
        
        if not val_list:
            return None, param_counter
        
        # 根据操作符构建条件
        if op == '$ne':
            if len(val_list) >= 1:
                param_name = f'cond_{param_counter}'
                param_counter += 1
                params[param_name] = val_list[0]
                return f'"{safe_field}" != :{param_name}', param_counter
        elif op == '$nin':
            placeholders = []
            for v in val_list:
                param_name = f'cond_{param_counter}'
                param_counter += 1
                placeholders.append(f':{param_name}')
                params[param_name] = v
            return f'"{safe_field}" NOT IN ({",".join(placeholders)})', param_counter
        elif op == '$in':
            placeholders = []
            for v in val_list:
                param_name = f'cond_{param_counter}'
                param_counter += 1
                placeholders.append(f':{param_name}')
                params[param_name] = v
            return f'"{safe_field}" IN ({",".join(placeholders)})', param_counter
        elif op == '$gt':
            param_name = f'cond_{param_counter}'
            param_counter += 1
            params[param_name] = val_list[0]
            return f'"{safe_field}" > :{param_name}', param_counter
        elif op == '$lt':
            param_name = f'cond_{param_counter}'
            param_counter += 1
            params[param_name] = val_list[0]
            return f'"{safe_field}" < :{param_name}', param_counter
        elif op == '$gte':
            param_name = f'cond_{param_counter}'
            param_counter += 1
            params[param_name] = val_list[0]
            return f'"{safe_field}" >= :{param_name}', param_counter
        elif op == '$lte':
            param_name = f'cond_{param_counter}'
            param_counter += 1
            params[param_name] = val_list[0]
            return f'"{safe_field}" <= :{param_name}', param_counter
        elif op == '$like' or op == '$regex':
            like_parts = []
            for v in val_list:
                param_name = f'cond_{param_counter}'
                param_counter += 1
                like_parts.append(f'LOWER(CAST("{safe_field}" AS TEXT)) LIKE LOWER(:{param_name})')
                params[param_name] = f'%{v}%'
            return '(' + ' OR '.join(like_parts) + ')', param_counter
        elif op == '$range':
            # $range: value 为 [start, end]，生成 field >= start AND field <= end
            if len(val_list) >= 2:
                p1 = f'cond_{param_counter}'
                param_counter += 1
                p2 = f'cond_{param_counter}'
                param_counter += 1
                params[p1] = val_list[0]
                params[p2] = val_list[1]
                return f'("{safe_field}" >= :{p1} AND "{safe_field}" <= :{p2})', param_counter
            elif len(val_list) == 1:
                param_name = f'cond_{param_counter}'
                param_counter += 1
                params[param_name] = val_list[0]
                return f'"{safe_field}" >= :{param_name}', param_counter
        elif op == '$nrange':
            # $nrange: value 为 [start, end]，生成 NOT (field >= start AND field <= end)
            if len(val_list) >= 2:
                p1 = f'cond_{param_counter}'
                param_counter += 1
                p2 = f'cond_{param_counter}'
                param_counter += 1
                params[p1] = val_list[0]
                params[p2] = val_list[1]
                return f'NOT ("{safe_field}" >= :{p1} AND "{safe_field}" <= :{p2})', param_counter
        else:
            if len(val_list) == 1:
                param_name = f'cond_{param_counter}'
                param_counter += 1
                params[param_name] = val_list[0]
                return f'"{safe_field}" = :{param_name}', param_counter
            else:
                placeholders = []
                for v in val_list:
                    param_name = f'cond_{param_counter}'
                    param_counter += 1
                    placeholders.append(f':{param_name}')
                    params[param_name] = v
                return f'"{safe_field}" IN ({",".join(placeholders)})', param_counter
        
        return None, param_counter
    
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
    def get_unique_attributes(model_id):
        """获取模型的唯一属性列表（从 cc_ObjectUnique 表读取）"""
        from app.service.model_service import ModelService
        
        unique_constraints = ModelService.get_object_unique(model_id)
        if not unique_constraints:
            return []
        
        attributes = ModelService.get_model_attributes(model_id)
        attr_map = {attr.get('id'): attr for attr in attributes}
        
        unique_attrs = []
        for constraint in unique_constraints:
            keys = constraint.get('keys', [])
            for key in keys:
                if key.get('key_kind') == 'property':
                    attr_id = key.get('key_id')
                    attr = attr_map.get(attr_id)
                    if attr and not attr.get('bk_isapi'):
                        unique_attrs.append(attr)
        
        return unique_attrs
    
    @staticmethod
    def get_object_unique_constraints(model_id):
        """获取模型的唯一约束定义（包含组合键）"""
        from app.service.model_service import ModelService
        
        constraints = ModelService.get_object_unique(model_id)
        if not constraints:
            return []
        
        attributes = ModelService.get_model_attributes(model_id)
        attr_map = {attr.get('id'): attr for attr in attributes}
        
        result = []
        for constraint in constraints:
            keys = constraint.get('keys', [])
            constraint_attrs = []
            for key in keys:
                if key.get('key_kind') == 'property':
                    attr_id = key.get('key_id')
                    attr = attr_map.get(attr_id)
                    if attr:
                        constraint_attrs.append(attr)
            if constraint_attrs:
                result.append({
                    'id': constraint.get('id'),
                    'keys': constraint_attrs
                })
        
        return result
    
    @staticmethod
    def check_unique(model_id, data, exclude_instance_id=None):
        """
        校验实例数据的唯一性（支持组合唯一键）
        :param model_id: 模型ID
        :param data: 实例数据 dict
        :param exclude_instance_id: 排除的实例ID（更新时用，排除自身）
        :return: list of dict [{property_id, property_name, value}] 重复的字段列表
        """
        table_name = InstanceService._get_table_name(model_id)
        unique_constraints = InstanceService.get_object_unique_constraints(model_id)

        if not unique_constraints:
            return []

        id_field = InstanceService._get_id_field(model_id)
        duplicates = []
        for constraint in unique_constraints:
            constraint_attrs = constraint.get('keys', [])
            
            all_keys_present = True
            key_values = {}
            key_names = []
            
            for attr in constraint_attrs:
                prop_id = attr.get('bk_property_id')
                prop_name = attr.get('bk_property_name', prop_id)
                value = data.get(prop_id)
                
                if value is None or value == '':
                    all_keys_present = False
                    break
                
                key_values[prop_id] = value
                key_names.append(prop_name)
            
            if not all_keys_present:
                continue
            
            sql_parts = [f'SELECT COUNT(*) as cnt FROM "{table_name}" WHERE']
            where_clauses = []
            params = {}
            
            for idx, (prop_id, value) in enumerate(key_values.items()):
                param_name = f'val_{idx}'
                where_clauses.append(f'"{prop_id}" = :{param_name}')
                params[param_name] = value
            
            sql_parts.append(' AND '.join(where_clauses))
            
            if exclude_instance_id is not None:
                sql_parts.append(f'AND "{id_field}" != :exclude_id')
                params['exclude_id'] = exclude_instance_id

            sql = ' '.join(sql_parts)
            result = query_one(sql, params)

            if result and result.get('cnt', 0) > 0:
                for prop_id, value in key_values.items():
                    attr = next((a for a in constraint_attrs if a.get('bk_property_id') == prop_id), None)
                    if attr:
                        duplicates.append({
                            'property_id': prop_id,
                            'property_name': attr.get('bk_property_name', prop_id),
                            'value': value
                        })

        # 去重：同一属性ID+值组合只保留一个（避免多约束同时触发时重复报错）
        seen = set()
        unique_duplicates = []
        for d in duplicates:
            key = (d['property_id'], d['value'])
            if key not in seen:
                seen.add(key)
                unique_duplicates.append(d)

        return unique_duplicates

    @staticmethod
    def create_instance(model_id, data):
        """创建实例"""
        # 检查模型是否已停用
        from app.service.model_service import ModelService
        model = ModelService.get_model_by_id(model_id)
        if model and model.get('bk_ispaused'):
            raise ValidationException(f'模型 {model.get("bk_obj_name", model_id)} 已停用，无法创建实例')

        table_name = InstanceService._get_table_name(model_id)
        id_field = InstanceService._get_id_field(model_id)

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 全局唯一 ID（单一计数器覆盖所有序列域，数据库无关）
        instance_id = generate_id(model_id=model_id)
        # 内置模型表无 id/bk_obj_id 列，只有业务主键列（bk_host_id 等）
        # 自定义模型表有 id（PK）+ bk_inst_id + bk_obj_id 列
        is_builtin = model_id in InstanceService.BUILTIN_ID_FIELD_MAP
        if not is_builtin:
            data['id'] = instance_id
            data['bk_obj_id'] = model_id
        data[id_field] = instance_id
        data.setdefault('bk_supplier_account', '0')
        # 内置时间字段由系统写入：调用方（含前端只读表单回传）给空值时一律取当前时间，
        # 仅在显式传入非空值（数据迁移场景）时保留原值。
        if not data.get('create_time'):
            data['create_time'] = now
        if not data.get('last_time'):
            data['last_time'] = now

        duplicates = InstanceService.check_unique(model_id, data)
        if duplicates:
            msg = '; '.join([f"{d['property_name']}已存在: {d['value']}" for d in duplicates])
            raise ValidationException(msg)

        # 清理字段，只保留安全字段
        from app.service.model_service import ModelService
        attributes = ModelService.get_model_attributes(model_id)
        # 构建属性ID到属性类型的映射
        attr_type_map = {}
        for attr in attributes:
            pid = attr.get('bk_property_id')
            if pid:
                attr_type_map[pid] = attr.get('bk_property_type', '')

        valid_fields = set([attr.get('bk_property_id') for attr in attributes])
        valid_fields.update(SYSTEM_FIELDS)

        clean_data = {}
        for key, value in data.items():
            if key in valid_fields:
                prop_type = attr_type_map.get(key, '')

                # 关联类型不落实例表列，跳过
                if prop_type in ASSOCIATION_PROPERTY_TYPES:
                    continue

                # objuser（MongoDB 为纯逗号拼接字符串）：原样保存为纯字符串，不 JSON 化
                if prop_type in OBJUSER_PROPERTY_TYPES:
                    if value is None:
                        clean_data[key] = None
                    elif isinstance(value, str):
                        clean_data[key] = value
                    elif isinstance(value, (list, tuple)):
                        # UI 传入数组时按 MongoDB 规则用逗号拼接为英文名串
                        clean_data[key] = ",".join(str(v).strip() for v in value)
                    else:
                        clean_data[key] = str(value)
                    continue

                # organization（MongoDB 为部门 ID 数组）：以 JSON 文本保存，读取时解析回数组
                if prop_type in JSON_VALUE_PROPERTY_TYPES:
                    if value is None:
                        clean_data[key] = None
                    elif isinstance(value, str):
                        clean_data[key] = value
                    else:
                        clean_data[key] = json.dumps(value)
                    continue

                if isinstance(value, (dict, list)):
                    clean_data[key] = json.dumps(value)
                elif value is None:
                    clean_data[key] = None
                elif prop_type == PROPERTY_TYPE_BOOL:
                    # bool 类型保持原生布尔值
                    if isinstance(value, bool):
                        clean_data[key] = value
                    elif isinstance(value, str):
                        clean_data[key] = value.lower() == 'true'
                    elif isinstance(value, int):
                        clean_data[key] = bool(value)
                    else:
                        clean_data[key] = bool(value)
                elif isinstance(value, (int, float)):
                    clean_data[key] = value
                else:
                    clean_data[key] = str(value)

        # 只保留目标表真实存在的列，过滤内置模型无对应列的元数据字段
        # （如 host 表的 bk_inst_name / id / bk_obj_id / bk_inst_id）。
        # 这些字段被 cc_ObjAttDes 列为属性，但内置表不含该列，写入会触发
        # "table cc_HostBase has no column named ..."，故在此按真实表结构收敛。
        real_cols = get_table_columns(table_name)
        clean_data = {k: v for k, v in clean_data.items() if k in real_cols}

        if not clean_data:
            raise ValidationException('No valid data to update')

        columns = list(clean_data.keys())
        placeholders = [f':{col}' for col in columns]

        sql = f'INSERT INTO "{table_name}" ({",".join([f"{col}" for col in columns])}) VALUES ({",".join(placeholders)})'
        execute(sql, clean_data)

        return InstanceService.get_instance(model_id, instance_id)
    
    @staticmethod
    def update_instance(model_id, instance_id, data):
        """更新实例"""
        table_name = InstanceService._get_table_name(model_id)
        id_field = InstanceService._get_id_field(model_id)

        # 最后修改时间由系统强制刷新（忽略调用方传入值）；创建时间在下方
        # system_fields_to_exclude 中被排除，任何更新请求都改不动。
        data['last_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        duplicates = InstanceService.check_unique(model_id, data, exclude_instance_id=instance_id)
        if duplicates:
            msg = '; '.join([f"{d['property_name']}已存在: {d['value']}" for d in duplicates])
            raise ValidationException(msg)

        # 获取有效字段
        from app.service.model_service import ModelService
        attributes = ModelService.get_model_attributes(model_id)
        # 构建属性ID到属性类型的映射
        attr_type_map = {}
        for attr in attributes:
            pid = attr.get('bk_property_id')
            if pid:
                attr_type_map[pid] = attr.get('bk_property_type', '')

        valid_fields = set([attr.get('bk_property_id') for attr in attributes])
        valid_fields.update(SYSTEM_FIELDS)
        # 不允许修改系统字段
        system_fields_to_exclude = ['id', '_id', 'bk_supplier_account', 'create_time']

        update_fields = []
        params = {'instance_id': instance_id}

        for key, value in data.items():
            if key in valid_fields and key not in system_fields_to_exclude and key in get_table_columns(table_name):
                prop_type = attr_type_map.get(key, '')

                # 关联类型不落实例表列，跳过
                if prop_type in ASSOCIATION_PROPERTY_TYPES:
                    continue

                update_fields.append(f'"{key}" = :{key}')
                # objuser（MongoDB 为纯逗号拼接字符串）：原样保存为纯字符串，不 JSON 化
                if prop_type in OBJUSER_PROPERTY_TYPES:
                    if value is None:
                        params[key] = None
                    elif isinstance(value, str):
                        params[key] = value
                    elif isinstance(value, (list, tuple)):
                        # UI 传入数组时按 MongoDB 规则用逗号拼接为英文名串
                        params[key] = ",".join(str(v).strip() for v in value)
                    else:
                        params[key] = str(value)
                    continue

                # organization（MongoDB 为部门 ID 数组）：以 JSON 文本保存，读取时解析回数组
                if prop_type in JSON_VALUE_PROPERTY_TYPES:
                    if value is None:
                        params[key] = None
                    elif isinstance(value, str):
                        params[key] = value
                    else:
                        params[key] = json.dumps(value)
                    continue

                if isinstance(value, (dict, list)):
                    params[key] = json.dumps(value)
                elif value is None:
                    params[key] = None
                elif prop_type == PROPERTY_TYPE_BOOL:
                    # bool 类型保持原生布尔值
                    if isinstance(value, bool):
                        params[key] = value
                    elif isinstance(value, str):
                        params[key] = value.lower() == 'true'
                    elif isinstance(value, int):
                        params[key] = bool(value)
                    else:
                        params[key] = bool(value)
                elif isinstance(value, (int, float)):
                    params[key] = value
                else:
                    params[key] = str(value)

        if not update_fields:
            return InstanceService.get_instance(model_id, instance_id)

        sql = f'UPDATE "{table_name}" SET {",".join(update_fields)} WHERE "{id_field}" = :instance_id'
        execute(sql, params)

        return InstanceService.get_instance(model_id, instance_id)
    
    @staticmethod
    def batch_update_instances(model_id, ids, data):
        """批量更新实例"""
        if not ids:
            return 0

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data['last_time'] = now

        # 获取模型属性（与 update_instance 一致）
        from app.service.model_service import ModelService
        attributes = ModelService.get_model_attributes(model_id)

        # 检查是否更新了唯一字段（与原项目保持一致，禁止批量更新唯一字段）
        unique_constraints = InstanceService.get_object_unique_constraints(model_id)
        unique_property_ids = set()
        for constraint in unique_constraints:
            keys = constraint.get('keys', [])
            for key in keys:
                property_id = key.get('bk_property_id')
                if property_id:
                    unique_property_ids.add(property_id)

        for field_name in data.keys():
            if field_name != 'last_time' and field_name in unique_property_ids:
                raise ValidationException('不允许批量更新唯一字段')

        table_name = InstanceService._get_table_name(model_id)
        id_field = InstanceService._get_id_field(model_id)

        # 构建属性ID到属性类型的映射
        attr_type_map = {}
        for attr in attributes:
            pid = attr.get('bk_property_id')
            if pid:
                attr_type_map[pid] = attr.get('bk_property_type', '')

        valid_fields = set([attr.get('bk_property_id') for attr in attributes])
        valid_fields.update(SYSTEM_FIELDS)
        # 不允许修改系统字段
        system_fields_to_exclude = ['id', '_id', 'bk_supplier_account', 'create_time']

        update_fields = []
        params = {}
        param_idx = 0

        for key, value in data.items():
            if key in valid_fields and key not in system_fields_to_exclude and key in get_table_columns(table_name):
                prop_type = attr_type_map.get(key, '')

                # 关联类型不落实例表列，跳过
                if prop_type in ASSOCIATION_PROPERTY_TYPES:
                    continue

                param_name = f'val_{param_idx}'
                update_fields.append(f'"{key}" = :{param_name}')
                # objuser（MongoDB 为纯逗号拼接字符串）：原样保存为纯字符串，不 JSON 化
                if prop_type in OBJUSER_PROPERTY_TYPES:
                    if value is None:
                        params[param_name] = None
                    elif isinstance(value, str):
                        params[param_name] = value
                    elif isinstance(value, (list, tuple)):
                        # UI 传入数组时按 MongoDB 规则用逗号拼接为英文名串
                        params[param_name] = ",".join(str(v).strip() for v in value)
                    else:
                        params[param_name] = str(value)
                    param_idx += 1
                    continue

                # organization（MongoDB 为部门 ID 数组）：以 JSON 文本保存，读取时解析回数组
                if prop_type in JSON_VALUE_PROPERTY_TYPES:
                    if value is None:
                        params[param_name] = None
                    elif isinstance(value, str):
                        params[param_name] = value
                    else:
                        params[param_name] = json.dumps(value)
                    param_idx += 1
                    continue

                if isinstance(value, (dict, list)):
                    params[param_name] = json.dumps(value)
                elif value is None:
                    params[param_name] = None
                elif prop_type == PROPERTY_TYPE_BOOL:
                    # bool 类型保持原生布尔值
                    if isinstance(value, bool):
                        params[param_name] = value
                    elif isinstance(value, str):
                        params[param_name] = value.lower() == 'true'
                    elif isinstance(value, int):
                        params[param_name] = bool(value)
                    else:
                        params[param_name] = bool(value)
                elif isinstance(value, (int, float)):
                    params[param_name] = value
                else:
                    params[param_name] = str(value)
                param_idx += 1

        if not update_fields:
            return len(ids)

        # 构建IN子句的参数
        id_params = []
        for idx, inst_id in enumerate(ids):
            param_name = f'id_{idx}'
            id_params.append(f':{param_name}')
            params[param_name] = inst_id

        sql = f'UPDATE "{table_name}" SET {",".join(update_fields)} WHERE "{id_field}" IN ({",".join(id_params)})'
        execute(sql, params)

        return len(ids)
    
    @staticmethod
    def delete_instances(model_id, ids):
        """删除实例（支持批量）"""
        table_name = InstanceService._get_table_name(model_id)
        id_field = InstanceService._get_id_field(model_id)
        
        if not ids:
            return 0
        
        # 先删除关联表中的记录（按模型分表，与原项目一致）
        # 1. 从该模型的分表删除作为源实例的关联
        # 2. 从该模型的分表删除作为目标实例的关联
        # 3. 从关联的对端模型分表清理冗余记录
        id_params = {f'id_{idx}': inst_id for idx, inst_id in enumerate(ids)}
        id_placeholders = ','.join([f':id_{idx}' for idx in range(len(ids))])
        
        # 获取该模型的实例关联分表名
        from app.service.association_service import get_inst_asst_table_name
        model_asst_table = get_inst_asst_table_name(model_id)
        
        # 先查出涉及的对端模型（用于清理对端分表冗余记录）
        try:
            related_models_sql = f'''
                SELECT DISTINCT bk_asst_obj_id FROM "{model_asst_table}"
                WHERE bk_obj_id = :model_id AND bk_inst_id IN ({id_placeholders})
            '''
            related_dest_models = query_all(related_models_sql, {'model_id': model_id, **id_params})
            
            related_src_models_sql = f'''
                SELECT DISTINCT bk_obj_id FROM "{model_asst_table}"
                WHERE bk_asst_obj_id = :model_id AND bk_asst_inst_id IN ({id_placeholders})
            '''
            related_src_models = query_all(related_src_models_sql, {'model_id': model_id, **id_params})
        except Exception:
            related_dest_models = []
            related_src_models = []
        
        # 从该模型分表删除（源 + 目标）
        delete_src_sql = f'DELETE FROM "{model_asst_table}" WHERE bk_obj_id = :model_id AND bk_inst_id IN ({id_placeholders})'
        execute(delete_src_sql, {'model_id': model_id, **id_params})
        
        delete_dest_sql = f'DELETE FROM "{model_asst_table}" WHERE bk_asst_obj_id = :model_id AND bk_asst_inst_id IN ({id_placeholders})'
        execute(delete_dest_sql, {'model_id': model_id, **id_params})
        
        # 从对端模型分表清理冗余记录
        for item in related_dest_models:
            dest_model_id = item.get('bk_asst_obj_id')
            if dest_model_id and dest_model_id != model_id:
                dest_table = get_inst_asst_table_name(dest_model_id)
                try:
                    sql = f'DELETE FROM "{dest_table}" WHERE bk_obj_id = :model_id AND bk_inst_id IN ({id_placeholders})'
                    execute(sql, {'model_id': model_id, **id_params})
                except Exception:
                    pass
        
        for item in related_src_models:
            src_model_id = item.get('bk_obj_id')
            if src_model_id and src_model_id != model_id:
                src_table = get_inst_asst_table_name(src_model_id)
                try:
                    sql = f'DELETE FROM "{src_table}" WHERE bk_asst_obj_id = :model_id AND bk_asst_inst_id IN ({id_placeholders})'
                    execute(sql, {'model_id': model_id, **id_params})
                except Exception:
                    pass
        
        # 删除实例表中的记录
        id_placeholders = ','.join([f':id_{idx}' for idx in range(len(ids))])
        delete_instance_sql = f'DELETE FROM "{table_name}" WHERE "{id_field}" IN ({id_placeholders})'
        execute(delete_instance_sql, id_params)
        
        return len(ids)
    
    @staticmethod
    def get_related_instances(instance_id, model_id=None):
        """获取实例的关联实例详情"""
        from app.service.association_service import AssociationService
        
        associations = AssociationService.get_instance_associations(instance_id)
        related_instances = []
        
        for assoc in associations:
            # 确定目标实例的模型和ID
            if assoc.get('bk_obj_id') == model_id or model_id is None:
                target_model_id = assoc.get('bk_asst_obj_id')
                target_instance_id = assoc.get('bk_asst_inst_id')
            elif assoc.get('bk_asst_obj_id') == model_id or model_id is None:
                target_model_id = assoc.get('bk_obj_id')
                target_instance_id = assoc.get('bk_inst_id')
            else:
                continue
            
            # 获取目标实例
            try:
                instance = InstanceService.get_instance(target_model_id, target_instance_id)
                if instance:
                    related_instances.append(instance)
            except Exception:
                # 如果实例不存在，跳过
                continue
        
        return related_instances


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
    'modifier',
    # 内置模型专用ID/名称字段
    'bk_host_id',
    'bk_host_name',
    'bk_biz_id',
    'bk_biz_name',
    'bk_set_id',
    'bk_set_name',
    'bk_module_id',
    'bk_module_name',
    'bk_biz_set_id',
    'bk_biz_set_name',
    'creator'                   # 实例创建者（RBAC「创建者自管」判定；对齐上游 owner 维度）
}
