#!/usr/bin/env python3
"""
CMDB Server Lite - HTTP Backend Server with DuckDB 1.0
"""

import os
import json
import re
import duckdb
from typing import Optional, Dict, List, Any, Tuple
from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
import time

app = FastAPI(title="CMDB Server Lite", version="1.0.0")
logger = logging.getLogger("uvicorn")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(__file__), "cmdb.duckdb")


def get_db():
    """获取数据库连接，每次操作都建立新连接，避免并发锁问题"""
    return duckdb.connect(DB_PATH, read_only=False)


def validate_string_with_regex(value: str, regex: str) -> Tuple[bool, str]:
    """验证字符串是否符合正则表达式"""
    try:
        if not re.fullmatch(regex, value):
            return False, f"值 '{value}' 不符合正则表达式规则: {regex}"
        return True, ""
    except re.error as e:
        return False, f"正则表达式格式错误: {str(e)}"


def validate_enum_value(value: Any, options: List[Any]) -> Tuple[bool, str]:
    """验证值是否在枚举选项列表中"""
    if not isinstance(options, list):
        return True, ""  # 如果option不是列表，跳过验证
    if value not in options:
        return False, f"值 '{value}' 不在允许的选项列表中: {options}"
    return True, ""


def validate_required_field(value: Any, field_name: str) -> Tuple[bool, str]:
    """验证必填字段"""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return False, f"字段 '{field_name}' 为必填项"
    return True, ""


def parse_option_value(option: Any) -> Any:
    """解析option字段值，处理JSON字符串和列表"""
    if isinstance(option, str):
        try:
            return json.loads(option)
        except (json.JSONDecodeError, TypeError):
            return option
    return option


def validate_instance_data(model_id: str, instance_data: Dict[str, Any], attributes: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """
    验证实例数据
    
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    # 获取模型的属性定义
    model_attrs = [attr for attr in attributes if attr.get('bk_obj_id') == model_id]
    
    for attr in model_attrs:
        field_name = attr.get('bk_property_id')
        field_type = attr.get('bk_property_type')
        is_required = attr.get('isrequired', False)
        option = parse_option_value(attr.get('option'))
        default_val = attr.get('default')
        
        value = instance_data.get(field_name)
        
        # 1. 验证必填字段
        if is_required:
            is_valid, err_msg = validate_required_field(value, field_name)
            if not is_valid:
                errors.append(err_msg)
                continue
        
        # 如果值为空且有默认值，使用默认值
        if (value is None or (isinstance(value, str) and value.strip() == "")) and default_val is not None:
            instance_data[field_name] = default_val
            value = default_val
        
        # 如果值仍然为空，跳过验证（非必填）
        if value is None or (isinstance(value, str) and value.strip() == ""):
            continue
        
        # 2. 根据字段类型进行验证
        if field_type in ['singlechar', 'longchar', 'char']:
            # 字符串类型：检查正则表达式
            if option and isinstance(option, str) and isinstance(value, str):
                is_valid, err_msg = validate_string_with_regex(value, option)
                if not is_valid:
                    errors.append(err_msg)
        elif field_type in ['enum', 'enumMulti']:
            # 枚举类型：检查值是否在选项中
            if option:
                if field_type == 'enumMulti':
                    # 多选：检查每个值
                    if isinstance(value, list):
                        for v in value:
                            is_valid, err_msg = validate_enum_value(v, option)
                            if not is_valid:
                                errors.append(err_msg)
                    else:
                        # 如果不是列表但有值，单个检查
                        is_valid, err_msg = validate_enum_value(value, option)
                        if not is_valid:
                            errors.append(err_msg)
                else:
                    # 单选
                    is_valid, err_msg = validate_enum_value(value, option)
                    if not is_valid:
                        errors.append(err_msg)
        elif field_type in ['int', 'number']:
            # 数字类型：验证转换
            try:
                if field_type == 'int':
                    int(value)
                else:
                    float(value)
            except (ValueError, TypeError):
                errors.append(f"字段 '{field_name}' 必须是数字类型")
        elif field_type == 'bool':
            # 布尔类型
            if not isinstance(value, bool) and value not in [0, 1, '0', '1', 'true', 'false']:
                errors.append(f"字段 '{field_name}' 必须是布尔类型")
    
    return len(errors) == 0, errors





def query_all(sql: str, params: list = None) -> List[Dict]:
    db = get_db()
    try:
        if params:
            result = db.execute(sql, params).fetchall()
        else:
            result = db.execute(sql).fetchall()
        columns = [desc[0] for desc in db.description]
        return [dict(zip(columns, row)) for row in result]
    finally:
        db.close()


def query_one(sql: str, params: list = None) -> Optional[Dict]:
    result = query_all(sql, params)
    return result[0] if result else None


def get_instance_table_name(model_id: str) -> str:
    """根据模型ID动态生成实例表名"""
    return f"cc_ObjectBase_0_pub_{model_id}"


def model_exists(model_id: str) -> bool:
    """检查模型是否存在"""
    try:
        result = query_one(
            "SELECT 1 FROM cc_ObjAttDes WHERE bk_obj_id = ? LIMIT 1",
            [model_id]
        )
        return result is not None
    except:
        return False


def get_search_columns(model_id: str) -> List[str]:
    """从 cc_ObjAttDes 表动态获取模型的搜索字段"""
    try:
        attributes = query_all(
            "SELECT bk_property_id FROM cc_ObjAttDes WHERE bk_obj_id = ? ORDER BY bk_property_index LIMIT 8",
            [model_id]
        )
        if attributes:
            return [attr["bk_property_id"] for attr in attributes]
        return ["id"]
    except:
        return ["id"]


def init_user_custom_table():
    """初始化用户配置表"""
    db = get_db()
    try:
        # 先删除旧表（如果存在）以避免结构问题
        try:
            db.execute("DROP TABLE IF EXISTS user_custom")
            db.execute("DROP SEQUENCE IF EXISTS user_custom_id_seq")
        except Exception as e:
            print(f"[DEBUG] Cleaning up old tables: {e}")
        
        # 先创建序列
        db.execute("""
            CREATE SEQUENCE IF NOT EXISTS user_custom_id_seq START 1
        """)
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS user_custom (
                id INTEGER PRIMARY KEY DEFAULT NEXTVAL('user_custom_id_seq'),
                user_name VARCHAR NOT NULL DEFAULT 'admin',
                config_key VARCHAR NOT NULL,
                config_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_name, config_key)
            )
        """)
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                user_name VARCHAR UNIQUE NOT NULL,
                display_name VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            INSERT OR IGNORE INTO users (id, user_name, display_name) 
            VALUES (1, 'admin', 'Administrator')
        """)
    finally:
        db.close()


init_user_custom_table()


@app.get("/")
async def root():
    return {"message": "CMDB Server Lite API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    try:
        db = get_db()
        try:
            db.execute("SELECT 1")
            db_status = "connected"
        finally:
            db.close()
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "service": "CMDB Server Lite",
        "version": "1.0.0",
        "database": {
            "status": db_status,
            "path": DB_PATH
        },
        "cors": {
            "allow_origins": ["*"],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"]
        }
    }


@app.get("/api/classifications")
async def list_classifications():
    """获取所有分类列表"""
    try:
        classifications = query_all("SELECT * FROM cc_ObjClassification ORDER BY id")
        return {"classifications": classifications}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/find/classificationobject")
async def find_classification_with_objects(request_data: dict = None):
    """
    查询分类及其下属模型信息
    对应原项目的 searchClassificationsObjects API
    返回格式: [{分类信息, bk_objects: [模型列表]}]
    """
    try:
        classifications = query_all("""
            SELECT * FROM cc_ObjClassification 
            WHERE bk_ishidden = FALSE OR bk_ishidden IS NULL
            ORDER BY id
        """)
        
        result = []
        for cls in classifications:
            classification_id = cls.get("bk_classification_id")
            
            objects = query_all("""
                SELECT * FROM cc_ObjDes 
                WHERE bk_classification_id = ? 
                AND (bk_ispaused = FALSE OR bk_ispaused IS NULL)
                AND (bk_ishidden = FALSE OR bk_ishidden IS NULL)
                ORDER BY obj_sort_number, bk_obj_id
            """, [classification_id])
            
            cls_item = dict(cls)
            cls_item["bk_objects"] = objects
            result.append(cls_item)
        
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/classifications/{classification_id}")
async def get_classification(classification_id: str):
    """获取单个分类详情"""
    try:
        classification = query_one(
            "SELECT * FROM cc_ObjClassification WHERE bk_classification_id = ?",
            [classification_id]
        )
        if not classification:
            raise HTTPException(status_code=404, detail="Classification not found")
        return {"classification": classification}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/classifications/{classification_id}/models")
async def get_classification_models(classification_id: str):
    """获取分类下的所有模型"""
    try:
        models = query_all(
            "SELECT * FROM cc_ObjDes WHERE bk_classification_id = ? ORDER BY obj_sort_number",
            [classification_id]
        )
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models")
async def list_models():
    try:
        models = query_all("SELECT * FROM cc_ObjDes")
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/{model_id}")
async def get_model(model_id: str):
    try:
        model = query_one("SELECT * FROM cc_ObjDes WHERE bk_obj_id = ?", [model_id])
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return {"model": model}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/{model_id}/attributes")
async def get_model_attributes(model_id: str):
    try:
        attributes = query_all(
            "SELECT * FROM cc_ObjAttDes WHERE bk_obj_id = ? ORDER BY bk_property_index",
            [model_id]
        )
        if not attributes:
            raise HTTPException(status_code=404, detail="Model attributes not found")
        for attr in attributes:
            if attr.get("bk_property_type") == "char":
                attr["bk_property_type"] = "singlechar"
            option_value = attr.get("option")
            if option_value:
                try:
                    attr["bk_property_option"] = json.loads(option_value)
                except (json.JSONDecodeError, TypeError):
                    attr["bk_property_option"] = option_value
            else:
                attr["bk_property_option"] = None
            attr["option"] = attr.get("bk_property_option")
            if "default_columns" in attr:
                del attr["default_columns"]
        return {"attributes": attributes}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/find/associationtype")
async def find_association_type(params: dict = {}):
    try:
        association_types = query_all("""
            SELECT * FROM cc_AsstDes
        """)
        return {"info": association_types}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/find/objectassociation")
async def find_object_association(params: dict = {}):
    try:
        condition = params.get("condition", {})
        bk_obj_id = condition.get("bk_obj_id")
        bk_asst_obj_id = condition.get("bk_asst_obj_id")
        
        sql = """
            SELECT 
                oa.*,
                ad.bk_asst_name,
                ad.src_des,
                ad.dest_des,
                ad.direction
            FROM cc_ObjAsst oa
            JOIN cc_AsstDes ad ON oa.bk_asst_id = ad.bk_asst_id
        """
        where_clauses = []
        query_params = []
        
        if bk_obj_id:
            where_clauses.append("oa.bk_obj_id = ?")
            query_params.append(bk_obj_id)
        
        if bk_asst_obj_id:
            where_clauses.append("oa.target_obj_id = ?")
            query_params.append(bk_asst_obj_id)
        
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        
        associations = query_all(sql, query_params)
        return associations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/find/{obj_id}")
async def find_instance_by_obj_id(obj_id: str, params: dict = {}):
    """
    根据模型ID查询实例详情
    obj_id: 模型ID（如 bk_host, bk_slb 等）
    params: 查询参数
        - condition: 查询条件，如 {"bk_obj_id": "xxx", "id": 123}
    """
    try:
        table_name = get_instance_table_name(obj_id)
        
        if not model_exists(obj_id):
            raise HTTPException(status_code=404, detail=f"Model '{obj_id}' not found")
        
        condition = params.get("condition", {})
        where_clauses = []
        query_params = []
        
        # 处理查询条件
        for field, value in condition.items():
            if value is not None:
                # 安全处理字段名（只允许字母、数字和下划线）
                if not field.replace('_', '').replace('-', '').isalnum():
                    continue
                
                # 处理 id 字段
                if field == "id":
                    where_clauses.append(f'"{field}" = ?')
                    query_params.append(int(value))
                else:
                    where_clauses.append(f'"{field}" = ?')
                    query_params.append(value)
        
        sql = f'SELECT * FROM "{table_name}"'
        
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        
        sql += " LIMIT 1"
        
        instance = query_one(sql, query_params)
        
        if instance:
            return instance
        else:
            return None
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] find_instance_by_obj_id failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/{model_id}/associations")
async def get_model_associations(model_id: str):
    try:
        associations = query_all("""
            SELECT 
                oa.bk_obj_id,
                oa.target_obj_id,
                oa.target_obj_name,
                oa.bk_asst_id AS relation_type_id,
                ad.bk_asst_name AS relation_type_name,
                oa.cardinality,
                ad.direction
            FROM cc_ObjAsst oa
            JOIN cc_AsstDes ad ON oa.bk_asst_id = ad.bk_asst_id
            WHERE oa.bk_obj_id = ?
        """, [model_id])
        return {"associations": associations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/{model_id}/instances")
async def list_instances(
    model_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    search: str = Query(None),
    search_field: str = Query(None),
    search_value: str = Query(None),
    fuzzy: bool = Query(False),
    sort: str = Query(None),
    order: str = Query("asc")
):
    table_name = get_instance_table_name(model_id)
    if not model_exists(model_id):
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        where_clause = ""
        
        if search_field and search_value:
            safe_field = search_field.strip()
            safe_value = search_value.strip()
            if fuzzy:
                like_value = f"%{safe_value}%"
                where_clause = f' WHERE LOWER(CAST("{safe_field}" AS VARCHAR)) LIKE LOWER(\'{like_value}\')'
            else:
                if "'" in safe_value:
                    safe_value = safe_value.replace("'", "''")
                where_clause = f' WHERE "{safe_field}" = \'{safe_value}\''
        elif search:
            search_columns = get_search_columns(model_id)
            safe_search = search.strip().replace("'", "''")
            like_pattern = f"%{safe_search}%"
            conditions = " OR ".join([f'LOWER(CAST("{col}" AS VARCHAR)) LIKE LOWER(\'{like_pattern}\')' for col in search_columns])
            where_clause = f" WHERE ({conditions})"

        sort_clause = ""
        if sort:
            # 解析 bk-table 排序格式: "-field" 表示降序，field 表示升序
            sort_str = str(sort).strip()
            if sort_str.startswith('-'):
                sort_field = sort_str[1:]
                sort_direction = "DESC"
            else:
                sort_field = sort_str
                sort_direction = "ASC"
            # 安全验证：只允许字母、数字和下划线
            if sort_field.replace('_', '').replace('-', '').isalnum():
                sort_clause = f' ORDER BY "{sort_field}" {sort_direction}'

        offset = (page - 1) * page_size
        sql = f'SELECT * FROM "{table_name}"{where_clause}{sort_clause} LIMIT {page_size} OFFSET {offset}'
        
        # 调试日志：打印实际执行的SQL
        logger.info(f"[SEARCH DEBUG] SQL: {sql}")
        
        instances = query_all(sql)

        count_sql = f'SELECT COUNT(*) as cnt FROM "{table_name}"{where_clause}'
        logger.info(f"[SEARCH DEBUG] COUNT SQL: {count_sql}")
        
        total = query_one(count_sql)
        total_count = total.get('cnt', 0) if total else 0

        return {
            "instances": instances,
            "page": page,
            "page_size": page_size,
            "total": total_count
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/models/{model_id}/instances/search")
async def list_instances_search(
    model_id: str,
    request_data: dict = None
):
    page = 1
    page_size = 20
    search = None
    search_field = None
    search_value = None
    search_values = None
    search_start = None  # 日期时间范围搜索-开始值
    search_end = None    # 日期时间范围搜索-结束值
    operator = None  # 新增操作符：$eq, $ne, $in, $nin, $like, $gt, $lt, $gte, $lte
    fuzzy = False
    sort = None
    order = "asc"
    # 支持多个条件的AND组合查询
    conditions = None  # 格式: [{"field": "id", "operator": "$ne", "value": "1001"}, {"field": "cpu", "operator": "$ne", "value": "4"}]

    if request_data:
        page = request_data.get('page', 1)
        page_size = request_data.get('page_size', 20)
        # 安全检查：限制page_size不超过1000
        if page_size > 1000:
            page_size = 1000
        if page_size < 1:
            page_size = 1
        search = request_data.get('search')
        search_field = request_data.get('search_field')
        search_value = request_data.get('search_value')
        search_values = request_data.get('search_values')
        search_start = request_data.get('search_start')  # 获取日期时间范围开始值
        search_end = request_data.get('search_end')      # 获取日期时间范围结束值
        operator = request_data.get('operator')
        fuzzy = request_data.get('fuzzy', False)
        sort = request_data.get('sort')
        order = request_data.get('order', 'asc')
        conditions = request_data.get('conditions')  # 获取多条件组合

    table_name = get_instance_table_name(model_id)
    if not model_exists(model_id):
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        where_clause = ""

        # 构建单个条件的SQL片段
        def build_single_condition(field, op, value):
            safe_field = field.strip()
            # 解析多个搜索值（支持逗号分隔）
            if isinstance(value, list):
                value_list = [str(v).strip() for v in value if v]
            elif isinstance(value, str):
                value_list = [v.strip() for v in value.split(',') if v.strip()]
            else:
                value_list = [str(value).strip()]
            
            if not value_list:
                return None
                
            # 清理每个值中的单引号
            safe_values = [v.replace("'", "''") for v in value_list]
            
            # 根据操作符构建查询条件
            if op == '$ne':
                if len(safe_values) >= 1:
                    safe_val = safe_values[0]
                    return f'"{safe_field}" != \'{safe_val}\''
            elif op == '$nin':
                in_values = "', '".join(safe_values)
                return f'"{safe_field}" NOT IN (\'{in_values}\')'
            elif op == '$in':
                in_values = "', '".join(safe_values)
                return f'"{safe_field}" IN (\'{in_values}\')'
            elif op == '$gt':
                safe_val = safe_values[0]
                return f'"{safe_field}" > \'{safe_val}\''
            elif op == '$lt':
                safe_val = safe_values[0]
                return f'"{safe_field}" < \'{safe_val}\''
            elif op == '$gte':
                safe_val = safe_values[0]
                return f'"{safe_field}" >= \'{safe_val}\''
            elif op == '$lte':
                safe_val = safe_values[0]
                return f'"{safe_field}" <= \'{safe_val}\''
            elif op == '$like' or op == '$regex':
                like_conditions = " OR ".join([
                    f'LOWER(CAST("{safe_field}" AS VARCHAR)) LIKE LOWER(\'%{v}%\')'
                    for v in safe_values
                ])
                return f'({like_conditions})'
            else:  # 默认等于操作符
                if len(safe_values) == 1:
                    safe_val = safe_values[0]
                    return f'"{safe_field}" = \'{safe_val}\''
                else:
                    in_values = "', '".join(safe_values)
                    return f'"{safe_field}" IN (\'{in_values}\')'
            return None

        # 处理多条件组合查询
        # 支持两种格式：
        # 格式1: [{"field": "xxx", "operator": "xxx", "value": "xxx"}]
        # 格式2: {"condition": "AND", "rules": [{"field": "xxx", "operator": "xxx", "value": "xxx"}]}
        rules = []
        logic_operator = "AND"
        
        if isinstance(conditions, dict) and 'rules' in conditions:
            rules = conditions.get('rules', [])
            logic_operator = conditions.get('condition', 'AND').upper()
        elif isinstance(conditions, list):
            rules = conditions
        
        if rules and isinstance(rules, list) and len(rules) > 0:
            condition_parts = []
            for cond in rules:
                if isinstance(cond, dict) and 'field' in cond and 'operator' in cond:
                    field = cond.get('field', '')
                    op = cond.get('operator', '$eq')
                    value = cond.get('value', '')
                    
                    # 映射前端操作符到后端操作符
                    operator_mapping = {
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
                    if op in operator_mapping:
                        op = operator_mapping[op]
                    
                    # 如果有fuzzy标志
                    is_fuzzy = cond.get('fuzzy', False) or fuzzy
                    if is_fuzzy:
                        op = '$regex'
                    
                    single_cond = build_single_condition(field, op, value)
                    if single_cond:
                        condition_parts.append(single_cond)
            
            if condition_parts:
                where_clause = " WHERE " + f" {logic_operator} ".join(condition_parts)
        elif search_field and (search_value or search_values or search_start or search_end):
            # 单条件查询（兼容旧接口，包含日期时间范围搜索）
            safe_field = search_field.strip()
            condition_parts = []
            
            # 处理日期时间范围搜索
            if search_start or search_end:
                if search_start:
                    safe_start = str(search_start).strip().replace("'", "''")
                    condition_parts.append(f'"{safe_field}" >= \'{safe_start}\'')
                if search_end:
                    safe_end = str(search_end).strip().replace("'", "''")
                    condition_parts.append(f'"{safe_field}" <= \'{safe_end}\'')
            else:
                # 处理普通搜索（兼容旧接口）
                # 解析多个搜索值（支持逗号分隔）
                if search_values:
                    value_list = [v.strip() for v in str(search_values).split(',') if v.strip()]
                elif search_value:
                    value_list = [search_value.strip()]
                else:
                    value_list = []

                if value_list:
                    # 清理每个值中的单引号
                    safe_values = [v.replace("'", "''") for v in value_list]
                    
                    # 根据操作符构建查询条件
                    if operator == '$ne':
                        # 不等于操作符：不等于某个值
                        if len(safe_values) >= 1:
                            safe_val = safe_values[0]
                            condition_parts.append(f'"{safe_field}" != \'{safe_val}\'')
                    elif operator == '$nin':
                        # 不包含在数组中
                        in_values = "', '".join(safe_values)
                        condition_parts.append(f'"{safe_field}" NOT IN (\'{in_values}\')')
                    elif operator == '$in':
                        # 包含在数组中
                        in_values = "', '".join(safe_values)
                        condition_parts.append(f'"{safe_field}" IN (\'{in_values}\')')
                    elif operator == '$gt':
                        # 大于
                        safe_val = safe_values[0]
                        condition_parts.append(f'"{safe_field}" > \'{safe_val}\'')
                    elif operator == '$lt':
                        # 小于
                        safe_val = safe_values[0]
                        condition_parts.append(f'"{safe_field}" < \'{safe_val}\'')
                    elif operator == '$gte':
                        # 大于等于
                        safe_val = safe_values[0]
                        condition_parts.append(f'"{safe_field}" >= \'{safe_val}\'')
                    elif operator == '$lte':
                        # 小于等于
                        safe_val = safe_values[0]
                        condition_parts.append(f'"{safe_field}" <= \'{safe_val}\'')
                    elif operator == '$like' or operator == '$regex' or fuzzy:
                        # 模糊匹配：使用 OR 连接多个 LIKE 条件
                        like_conditions = " OR ".join([
                            f'LOWER(CAST("{safe_field}" AS VARCHAR)) LIKE LOWER(\'%{v}%\')'
                            for v in safe_values
                        ])
                        condition_parts.append(f"({like_conditions})")
                    else:
                        # 默认为等于操作符
                        if len(safe_values) == 1:
                            safe_val = safe_values[0]
                            condition_parts.append(f'"{safe_field}" = \'{safe_val}\'')
                        else:
                            # 多个值使用 IN
                            in_values = "', '".join(safe_values)
                            condition_parts.append(f'"{safe_field}" IN (\'{in_values}\')')
            
            if condition_parts:
                where_clause = " WHERE " + " AND ".join(condition_parts)
        
        elif search:
            search_columns = get_search_columns(model_id)
            safe_search = search.strip().replace("'", "''")
            like_pattern = f"%{safe_search}%"
            conditions = " OR ".join([f'LOWER(CAST("{col}" AS VARCHAR)) LIKE LOWER(\'{like_pattern}\')' for col in search_columns])
            where_clause = f" WHERE ({conditions})"

        sort_clause = ""
        if sort:
            # 解析 bk-table 排序格式: "-field" 表示降序，field 表示升序
            sort_str = str(sort).strip()
            if sort_str.startswith('-'):
                sort_field = sort_str[1:]
                sort_direction = "DESC"
            else:
                sort_field = sort_str
                sort_direction = "ASC"
            # 安全验证：只允许字母、数字和下划线
            if sort_field.replace('_', '').replace('-', '').isalnum():
                sort_clause = f' ORDER BY "{sort_field}" {sort_direction}'

        offset = (page - 1) * page_size
        sql = f'SELECT * FROM "{table_name}"{where_clause}{sort_clause} LIMIT {page_size} OFFSET {offset}'
        instances = query_all(sql)

        count_sql = f'SELECT COUNT(*) as cnt FROM "{table_name}"{where_clause}'
        total = query_one(count_sql)
        total_count = total.get('cnt', 0) if total else 0

        return {
            "instances": instances,
            "page": page,
            "page_size": page_size,
            "total": total_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/{model_id}/instances/{instance_id}")
async def get_instance(model_id: str, instance_id: int):
    table_name = get_instance_table_name(model_id)
    if not model_exists(model_id):
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        sql = f'SELECT * FROM "{table_name}" WHERE id = {instance_id}'
        instance = query_one(sql)
        if not instance:
            raise HTTPException(status_code=404, detail="Instance not found")
        
        # 简单处理 None，直接返回数据
        result_instance = {}
        for k, v in instance.items():
            if v is None:
                result_instance[k] = ""
            else:
                result_instance[k] = v
        
        return {"instance": result_instance}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/instances/{instance_id}/associations")
async def get_instance_associations(instance_id: int):
    try:
        associations = query_all(
            "SELECT * FROM cc_InstAsst_0_pub WHERE bk_inst_id = ? OR bk_asst_inst_id = ?",
            [instance_id, instance_id]
        )
        return {"associations": associations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create/instassociation")
async def create_inst_association(params: dict):
    try:
        print("\n" + "="*60)
        print("[CREATE INSTASSOCIATION] Request received")
        print(f"[CREATE INSTASSOCIATION] Full params: {params}")
        
        bk_obj_id = params.get("bk_obj_id")
        bk_inst_id = params.get("bk_inst_id")
        bk_asst_obj_id = params.get("bk_asst_obj_id")
        bk_asst_inst_id = params.get("bk_asst_inst_id")
        bk_obj_asst_id = params.get("bk_obj_asst_id")
        bk_relation_type_id = params.get("bk_relation_type_id")
        
        print(f"[CREATE INSTASSOCIATION] bk_obj_id: {bk_obj_id}")
        print(f"[CREATE INSTASSOCIATION] bk_inst_id: {bk_inst_id} (type: {type(bk_inst_id)})")
        print(f"[CREATE INSTASSOCIATION] bk_asst_obj_id: {bk_asst_obj_id}")
        print(f"[CREATE INSTASSOCIATION] bk_asst_inst_id: {bk_asst_inst_id} (type: {type(bk_asst_inst_id)})")
        print(f"[CREATE INSTASSOCIATION] bk_obj_asst_id: {bk_obj_asst_id}")
        print(f"[CREATE INSTASSOCIATION] bk_relation_type_id: {bk_relation_type_id}")
        
        if not all([bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id, bk_obj_asst_id, bk_relation_type_id]):
            print(f"[CREATE INSTASSOCIATION] ❌ Missing parameters!")
            raise HTTPException(status_code=400, detail="Missing required parameters")
        
        db = get_db()
        max_id = query_one("SELECT MAX(id) as max_id FROM cc_InstAsst_0_pub")
        new_id = (max_id.get('max_id', 0) or 0) + 1
        
        _id = f"{bk_obj_id}_{bk_inst_id}_{bk_asst_obj_id}_{bk_asst_inst_id}"
        
        print(f"[CREATE INSTASSOCIATION] Inserting record:")
        print(f"  _id: {_id}")
        print(f"  id: {new_id}")
        
        db.execute("""
            INSERT INTO cc_InstAsst_0_pub
            (_id, id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id, bk_obj_asst_id, bk_relation_type_id, bk_supplier_account)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [_id, new_id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id, bk_obj_asst_id, bk_relation_type_id, "0"])
        
        print(f"[CREATE INSTASSOCIATION] ✅ Success! New ID: {new_id}")
        print("="*60)
        
        return {"id": new_id, "result": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[CREATE INSTASSOCIATION] ❌ Error: {str(e)}")
        print("="*60)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete/instassociation/{obj_id}/{inst_asst_id}")
async def delete_inst_association(obj_id: str, inst_asst_id: int):
    try:
        db = get_db()
        
        # 确保 inst_asst_id 是整数
        inst_asst_id = int(inst_asst_id)
        
        # 只通过 id 查询记录，不验证 obj_id，因为关联可以从任何一侧删除
        existing = db.execute(
            "SELECT * FROM cc_InstAsst_0_pub WHERE id = ?",
            [inst_asst_id]
        ).fetchall()
        
        if not existing:
            return {"result": False, "message": "记录不存在"}
        
        # 执行删除，只通过 id 删除
        db.execute(
            "DELETE FROM cc_InstAsst_0_pub WHERE id = ?",
            [inst_asst_id]
        )
        
        # 获取删除的行数
        deleted_count = len(existing)
        db.commit()
        
        print(f"[DELETE] 删除了 {deleted_count} 条记录, id={inst_asst_id}")
        return {"result": True, "deleted": deleted_count}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/find/instassociation")
async def find_inst_association(params: dict):
    try:
        # 支持顶级 bk_obj_id 参数（与 condition 内部参数并存）
        bk_obj_id = params.get("bk_obj_id")
        condition = params.get("condition", {})
        
        sql = "SELECT * FROM cc_InstAsst_0_pub"
        where_clauses = []
        query_params = []
        
        # 顶级参数优先
        if bk_obj_id:
            where_clauses.append("bk_obj_id = ?")
            query_params.append(bk_obj_id)
        
        # 支持多个查询条件
        if condition.get("bk_obj_id"):
            if not bk_obj_id:  # 只有在顶级参数没有设置时才使用 condition 中的
                where_clauses.append("bk_obj_id = ?")
                query_params.append(condition["bk_obj_id"])
        
        if condition.get("bk_inst_id") is not None:
            where_clauses.append("bk_inst_id = ?")
            query_params.append(condition["bk_inst_id"])
        
        if condition.get("bk_asst_obj_id"):
            where_clauses.append("bk_asst_obj_id = ?")
            query_params.append(condition["bk_asst_obj_id"])
        
        if condition.get("bk_asst_inst_id") is not None:
            where_clauses.append("bk_asst_inst_id = ?")
            query_params.append(condition["bk_asst_inst_id"])
        
        if condition.get("bk_asst_id"):
            where_clauses.append("bk_relation_type_id = ?")
            query_params.append(condition["bk_asst_id"])
        
        if condition.get("bk_obj_asst_id"):
            where_clauses.append("bk_obj_asst_id = ?")
            query_params.append(condition["bk_obj_asst_id"])
        
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        
        associations = query_all(sql, query_params)
        return {"info": associations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/instances/{instance_id}/related")
async def get_related_instances(instance_id: int, model_id: str = None):
    try:
        if model_id:
            related = query_all(
                """SELECT a.*, ad.bk_asst_name as bk_relation_type_name, 
                          oa.bk_obj_id as bk_src_model, oa.target_obj_id as bk_dst_model
                   FROM cc_InstAsst_0_pub a
                   JOIN cc_AsstDes ad ON a.bk_relation_type_id = ad.bk_asst_id
                   JOIN cc_ObjAsst oa ON a.bk_obj_asst_id = oa.bk_obj_asst_id
                   WHERE (a.bk_inst_id = ? OR a.bk_asst_inst_id = ?) AND a.bk_obj_id = ?""",
                [instance_id, instance_id, model_id]
            )
        else:
            related = query_all(
                """SELECT a.*, ad.bk_asst_name as bk_relation_type_name, 
                          oa.bk_obj_id as bk_src_model, oa.target_obj_id as bk_dst_model
                   FROM cc_InstAsst_0_pub a
                   JOIN cc_AsstDes ad ON a.bk_relation_type_id = ad.bk_asst_id
                   JOIN cc_ObjAsst oa ON a.bk_obj_asst_id = oa.bk_obj_asst_id
                   WHERE a.bk_inst_id = ? OR a.bk_asst_inst_id = ?""",
                [instance_id, instance_id]
            )
        return {"related": related}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/relations")
async def list_relations():
    try:
        relations = query_all(
            """SELECT 
                 oa.bk_asst_id as bk_relation_type_id, 
                 ad.bk_asst_name as bk_relation_type_name, 
                 oa.bk_obj_id as bk_src_model, 
                 oa.target_obj_id as bk_dst_model, 
                 oa.cardinality
               FROM cc_ObjAsst oa
               JOIN cc_AsstDes ad ON oa.bk_asst_id = ad.bk_asst_id"""
        )
        return {"relations": relations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/statistics")
async def get_statistics():
    try:
        stats = {}
        models = query_all("SELECT DISTINCT bk_obj_id FROM cc_ObjAttDes")
        for model in models:
            model_id = model["bk_obj_id"]
            table_name = get_instance_table_name(model_id)
            result = query_one(f'SELECT COUNT(*) as cnt FROM "{table_name}"')
            stats[table_name] = result.get('cnt', 0) if result else 0
        return {"statistics": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )


@app.post("/api/usercustom/user/search")
async def search_user_custom(
    request_data: dict = None,
    x_user_name: str = Header(None, alias="x-user-name")
):
    """获取用户配置"""
    user_name = x_user_name if x_user_name else "admin"
    try:
        db = get_db()
        result = db.execute(
            "SELECT config_key, config_value FROM user_custom WHERE user_name = ?",
            [user_name]
        ).fetchall()
        
        usercustom = {}
        for row in result:
            config_key = row[0]
            config_value = row[1]
            if config_value:
                try:
                    usercustom[config_key] = json.loads(config_value)
                except json.JSONDecodeError:
                    usercustom[config_key] = config_value
        
        return usercustom
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/usercustom")
async def save_user_custom(
    usercustom: dict = None,
    x_user_name: str = Header(None, alias="x-user-name")
):
    """保存用户配置"""
    user_name = x_user_name if x_user_name else "admin"
    if not usercustom:
        return {"message": "No custom data to save"}
    
    try:
        from datetime import datetime
        db = get_db()
        now = datetime.now().isoformat()
        
        for config_key, config_value in usercustom.items():
            config_value_json = json.dumps(config_value) if not isinstance(config_value, str) else config_value
            
            db.execute("""
                INSERT INTO user_custom (user_name, config_key, config_value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_name, config_key) 
                DO UPDATE SET config_value = excluded.config_value, updated_at = excluded.updated_at
            """, [user_name, config_key, config_value_json, now])
        
        return {"message": "User custom saved successfully", "user_name": user_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users")
async def list_users():
    """获取用户列表"""
    try:
        users = query_all("SELECT * FROM users ORDER BY id")
        return {"users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/usercustom/model/{obj_id}")
async def get_model_user_custom(
    obj_id: str,
    x_user_name: str = Header(None, alias="x-user-name")
):
    """获取模型的列配置"""
    user_name = x_user_name if x_user_name else "admin"
    config_key = f"{obj_id}_custom_table_columns"
    
    try:
        db = get_db()
        print(f"[DEBUG] get_model_user_custom - user_name: {user_name}, obj_id: {obj_id}, config_key: {config_key}")
        
        result = db.execute(
            "SELECT config_value FROM user_custom WHERE user_name = ? AND config_key = ?",
            [user_name, config_key]
        ).fetchone()
        
        print(f"[DEBUG] get_model_user_custom - query result: {result}")
        
        if result and result[0]:
            try:
                columns = json.loads(result[0])
                print(f"[DEBUG] get_model_user_custom - parsed columns: {columns}")
                return {"columns": columns}
            except json.JSONDecodeError as e:
                print(f"[DEBUG] get_model_user_custom - JSON decode error: {e}")
                return {"columns": []}
        
        print(f"[DEBUG] get_model_user_custom - no config found, returning empty")
        return {"columns": []}
    except Exception as e:
        print(f"[ERROR] get_model_user_custom - exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/usercustom/model/{obj_id}")
async def save_model_user_custom(
    obj_id: str,
    request_data: dict = None,
    x_user_name: str = Header(None, alias="x-user-name")
):
    """保存模型的列配置"""
    user_name = x_user_name if x_user_name else "admin"
    config_key = f"{obj_id}_custom_table_columns"
    
    columns = request_data.get('columns', []) if request_data else []
    
    try:
        from datetime import datetime
        db = get_db()
        now = datetime.now().isoformat()
        columns_json = json.dumps(columns)
        
        print(f"[DEBUG] save_model_user_custom - user_name: {user_name}, obj_id: {obj_id}, config_key: {config_key}")
        print(f"[DEBUG] save_model_user_custom - request_data: {request_data}")
        print(f"[DEBUG] save_model_user_custom - columns to save: {columns}")
        print(f"[DEBUG] save_model_user_custom - columns_json: {columns_json}")
        
        db.execute("""
            INSERT INTO user_custom (user_name, config_key, config_value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_name, config_key) 
            DO UPDATE SET config_value = excluded.config_value, updated_at = excluded.updated_at
        """, [user_name, config_key, columns_json, now])
        
        print(f"[DEBUG] save_model_user_custom - save successful!")
        return {"message": "Model custom saved successfully", "obj_id": obj_id, "columns": columns}
    except Exception as e:
        print(f"[ERROR] save_model_user_custom - exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/models/{model_id}/instances/check-associations")
async def check_instance_associations(
    model_id: str,
    request_data: dict = None
):
    """检查实例的关联关系数量
    
    请求示例：
    {
        "ids": [1, 2, 3]
    }
    """
    if not model_exists(model_id):
        raise HTTPException(status_code=404, detail="Model not found")
    
    if not request_data or 'ids' not in request_data:
        raise HTTPException(status_code=400, detail="ids parameter is required")
    
    ids = request_data['ids']
    if not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="ids must be a list")
    
    if len(ids) == 0:
        raise HTTPException(status_code=400, detail="ids list cannot be empty")
    
    try:
        db = get_db()
        placeholders = ','.join(['?' for _ in ids])
        
        # 检查作为源的关联
        source_count_result = query_one(
            f'SELECT COUNT(*) as count FROM cc_InstAsst_0_pub WHERE bk_obj_id = ? AND bk_inst_id IN ({placeholders})',
            [model_id] + ids
        )
        source_count = source_count_result.get('count', 0) if source_count_result else 0
        
        # 检查作为目标的关联
        target_count_result = query_one(
            f'SELECT COUNT(*) as count FROM cc_InstAsst_0_pub WHERE bk_asst_obj_id = ? AND bk_asst_inst_id IN ({placeholders})',
            [model_id] + ids
        )
        target_count = target_count_result.get('count', 0) if target_count_result else 0
        
        total_count = source_count + target_count
        
        return {
            "total_associations": total_count,
            "source_associations": source_count,
            "target_associations": target_count,
            "instance_count": len(ids),
            "model_id": model_id
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/models/{model_id}/instances")
async def create_instance(
    model_id: str,
    request_data: dict = None
):
    """
    创建新的模型实例
    
    请求示例:
    {
        "data": {
            "field1": "value1",
            "field2": "value2"
        }
    }
    """
    table_name = get_instance_table_name(model_id)
    if not model_exists(model_id):
        raise HTTPException(status_code=404, detail="Model not found")
    
    if not request_data or 'data' not in request_data:
        raise HTTPException(status_code=400, detail="data field is required in request body")
    
    instance_data = request_data['data']
    
    try:
        db = get_db()
        
        # 获取模型的属性定义
        attributes = query_all('SELECT * FROM cc_ObjAttDes')
        
        # 0. 过滤掉系统字段 - 只读字段、id、时间字段等
        model_attrs = [attr for attr in attributes if attr.get('bk_obj_id') == model_id]
        filtered_data = {}
        for field_name, value in instance_data.items():
            # 检查是否是系统字段或只读字段
            attr = next((a for a in model_attrs if a.get('bk_property_id') == field_name), None)
            if attr:
                is_readonly = attr.get('isreadonly', False)
                is_editable = attr.get('editable', True)
                if is_readonly or not is_editable:
                    continue  # 跳过只读字段
            # 跳过系统字段
            if field_name in ['id', 'create_time', 'last_time', 'bk_operate_time']:
                continue
            filtered_data[field_name] = value
        
        instance_data = filtered_data
        
        # 1. 验证实例数据
        is_valid, errors = validate_instance_data(model_id, instance_data, attributes)
        if not is_valid:
            raise HTTPException(status_code=400, detail={"errors": errors})
        
        # 2. 获取表结构，自动生成缺失字段的默认值
        columns_result = db.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        columns = {col[1]: col for col in columns_result}
        
        # 3. 填充系统字段
        current_timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # 填充默认字段 - 只填充表中实际存在的字段
        if 'bk_supplier_account' in columns and 'bk_supplier_account' not in instance_data:
            instance_data['bk_supplier_account'] = '0'
        
        # 填充时间字段
        if 'create_time' in columns and 'create_time' not in instance_data:
            instance_data['create_time'] = current_timestamp
        if 'last_time' in columns and 'last_time' not in instance_data:
            instance_data['last_time'] = current_timestamp
        
        # 生成 bk_inst_id 字段（如果需要）- 与 id 保持一致
        if 'bk_inst_id' in columns and 'bk_inst_id' not in instance_data:
            max_result = query_one(f'SELECT MAX(bk_inst_id) as max_id FROM "{table_name}"')
            new_bk_inst_id = (max_result.get('max_id') or 0) + 1
            instance_data['bk_inst_id'] = new_bk_inst_id
        
        # DuckDB INTEGER PRIMARY KEY 不会自动递增，需要手动生成 id
        new_id = None
        if 'id' in columns and 'id' not in instance_data:
            max_result = query_one(f'SELECT MAX(id) as max_id FROM "{table_name}"')
            new_id = (max_result.get('max_id') or 0) + 1
            instance_data['id'] = new_id
        else:
            new_id = instance_data.get('id')
        if '_id' in columns and '_id' not in instance_data:
            instance_data['_id'] = str(new_id or '')
        
        # 4. 构建INSERT语句
        field_names = list(instance_data.keys())
        placeholders = [f'"{name}"' for name in field_names]
        value_placeholders = [f'?' for _ in field_names]
        values = [instance_data[name] for name in field_names]
        
        insert_sql = f'INSERT INTO "{table_name}" ({", ".join(placeholders)}) VALUES ({", ".join(value_placeholders)})'
        db.execute(insert_sql, values)
        
        # 5. 获取新创建的实例
        new_instance = query_one(f'SELECT * FROM "{table_name}" WHERE id = ?', [new_id])
        
        print(f"[INFO] Created new instance in {table_name} with id={new_id}")
        
        return {
            "success": True,
            "data": new_instance,
            "message": "实例创建成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/models/{model_id}/instances/{instance_id}")
async def update_instance(
    model_id: str,
    instance_id: int,
    request_data: dict = None
):
    """更新单个实例
    
    请求示例：
    {
        "field1": "value1",
        "field2": "value2"
    }
    """
    table_name = get_instance_table_name(model_id)
    if not model_exists(model_id):
        raise HTTPException(status_code=404, detail="Model not found")
    
    if not request_data:
        raise HTTPException(status_code=400, detail="Request data is required")
    
    try:
        db = get_db()
        
        # 先检查实例是否存在
        existing = db.execute(
            f'SELECT id FROM "{table_name}" WHERE id = ?',
            [instance_id]
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Instance not found")
        
        # 获取属性定义用于验证
        all_attributes = query_all('SELECT * FROM cc_ObjAttDes')
        attributes = [attr for attr in all_attributes if attr.get('bk_obj_id') == model_id]
        
        # 获取表结构
        columns_result = db.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        columns = {col[1]: col for col in columns_result}
        
        # 构建更新语句
        update_fields = []
        update_values = []
        
        # 添加自动更新的系统字段
        current_timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        if 'last_time' in columns:
            update_fields.append('"last_time" = ?')
            update_values.append(current_timestamp)
        
        for field, value in request_data.items():
            # 跳过 id 字段
            if field == 'id' or field == 'bk_inst_id':
                continue
                
            # 跳过系统字段，这些字段已经在上面添加了
            if field in ['last_time', 'create_time', 'bk_supplier_account']:
                continue
                
            # 验证字段
            field_attr = next((attr for attr in attributes if attr.get('bk_property_id') == field), None)
            if field_attr:
                is_readonly = field_attr.get('isreadonly', False)
                if is_readonly:
                    # 只读字段，跳过更新
                    continue
            
            update_fields.append(f'"{field}" = ?')
            update_values.append(value)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        update_values.append(instance_id)
        
        # 执行更新
        db.execute(
            f'UPDATE "{table_name}" SET {", ".join(update_fields)} WHERE id = ?',
            update_values
        )
        
        print(f"[INFO] Updated instance {instance_id} in {table_name}")
        
        # 获取更新后的实例
        updated_instance = db.execute(
            f'SELECT * FROM "{table_name}" WHERE id = ?',
            [instance_id]
        ).fetchone()
        
        columns = [desc[0] for desc in db.description]
        result = dict(zip(columns, updated_instance))
        
        return {
            "success": True,
            "data": result,
            "message": "Instance updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/models/{model_id}/instances")
async def batch_update_instances(
    model_id: str,
    request_data: dict = None
):
    """批量更新实例
    
    请求示例（两种格式都支持）：
    格式1：
    {
        "update": [
            {"datas": {"field1": "value1"}, "inst_id": 1},
            {"datas": {"field1": "value2"}, "inst_id": 2}
        ]
    }
    
    格式2：
    {
        "ids": [1, 2, 3],
        "data": {"field1": "value1", "field2": "value2"}
    }
    """
    table_name = get_instance_table_name(model_id)
    if not model_exists(model_id):
        raise HTTPException(status_code=404, detail="Model not found")
    
    if not request_data:
        raise HTTPException(status_code=400, detail="Request data is required")
    
    try:
        db = get_db()
        
        # 获取属性定义
        all_attributes = query_all('SELECT * FROM cc_ObjAttDes')
        attributes = [attr for attr in all_attributes if attr.get('bk_obj_id') == model_id]
        
        # 获取表的实际列名
        table_columns = db.execute(f'SELECT * FROM "{table_name}" LIMIT 0').description
        valid_columns = set(col[0] for col in table_columns)
        
        # 获取表结构
        columns_result = db.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        columns = {col[1]: col for col in columns_result}
        
        # 准备自动更新的系统字段
        current_timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        auto_update_fields = []
        auto_update_values = []
        if 'last_time' in columns:
            auto_update_fields.append('"last_time" = ?')
            auto_update_values.append(current_timestamp)
        
        updated_count = 0
        updated_ids = []
        
        # 支持两种请求格式
        if 'update' in request_data:
            # 格式1：每个实例有不同数据
            updates = request_data['update']
            for update_item in updates:
                inst_id = update_item.get('inst_id')
                datas = update_item.get('datas', {})
                
                if not inst_id or not datas:
                    continue
                
                # 先检查实例是否存在
                existing = db.execute(
                    f'SELECT id FROM "{table_name}" WHERE id = ?',
                    [inst_id]
                ).fetchone()
                if not existing:
                    continue
                
                # 构建更新语句 - 先添加自动更新的系统字段
                update_fields = auto_update_fields.copy()
                update_values = auto_update_values.copy()
                
                for field, value in datas.items():
                    if field == 'id' or field == 'bk_inst_id':
                        continue
                        
                    # 跳过系统字段，这些字段已经在上面添加了
                    if field in ['last_time', 'create_time', 'bk_supplier_account']:
                        continue
                    
                    # 检查字段是否存在于表中
                    if field not in valid_columns:
                        print(f"[WARN] Field '{field}' not found in table '{table_name}', skipping...")
                        continue
                    
                    field_attr = next((attr for attr in attributes if attr.get('bk_property_id') == field), None)
                    if field_attr and field_attr.get('isreadonly', False):
                        continue
                    
                    update_fields.append(f'"{field}" = ?')
                    update_values.append(value)
                
                if not update_fields:
                    continue
                
                update_values.append(inst_id)
                
                db.execute(
                    f'UPDATE "{table_name}" SET {", ".join(update_fields)} WHERE id = ?',
                    update_values
                )
                updated_count += 1
                updated_ids.append(inst_id)
        
        elif 'ids' in request_data and 'data' in request_data:
            # 格式2：多个实例使用相同数据
            ids = request_data['ids']
            data = request_data['data']
            
            if not isinstance(ids, list) or len(ids) == 0:
                raise HTTPException(status_code=400, detail="ids must be a non-empty list")
            
            # 构建更新语句 - 先添加自动更新的系统字段
            update_fields = auto_update_fields.copy()
            update_values = auto_update_values.copy()
            skipped_fields = []
            
            for field, value in data.items():
                if field == 'id' or field == 'bk_inst_id':
                    continue
                    
                # 跳过系统字段，这些字段已经在上面添加了
                if field in ['last_time', 'create_time', 'bk_supplier_account']:
                    continue
                
                # 检查字段是否存在于表中
                if field not in valid_columns:
                    print(f"[WARN] Field '{field}' not found in table '{table_name}', skipping...")
                    skipped_fields.append(f"{field} (not in table)")
                    continue
                
                field_attr = next((attr for attr in attributes if attr.get('bk_property_id') == field), None)
                if field_attr and field_attr.get('isreadonly', False):
                    print(f"[WARN] Field '{field}' is readonly, skipping...")
                    skipped_fields.append(f"{field} (readonly)")
                    continue
                
                update_fields.append(f'"{field}" = ?')
                update_values.append(value)
            
            if not update_fields:
                error_msg = f"No valid fields to update. Requested fields: {list(data.keys())}, Valid columns in table: {list(valid_columns)}, Skipped: {skipped_fields}"
                print(f"[ERROR] {error_msg}")
                raise HTTPException(status_code=400, detail=error_msg)
            
            # 批量更新
            placeholders = ','.join(['?' for _ in ids])
            update_values.extend(ids)
            
            result = db.execute(
                f'UPDATE "{table_name}" SET {", ".join(update_fields)} WHERE id IN ({placeholders})',
                update_values
            )
            
            updated_count = result.rowcount if hasattr(result, 'rowcount') else len(ids)
            updated_ids = ids
        
        else:
            raise HTTPException(status_code=400, detail="Invalid request format")
        
        print(f"[INFO] Batch updated {updated_count} instances in {table_name}")
        
        return {
            "success": True,
            "updated_count": updated_count,
            "updated_ids": updated_ids,
            "message": f"Successfully updated {updated_count} instances"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/models/{model_id}/instances")
async def delete_instances(
    model_id: str,
    request_data: dict = None
):
    """删除实例，支持批量删除
    
    请求示例：
    {
        "ids": [1, 2, 3]
    }
    """
    table_name = get_instance_table_name(model_id)
    if not model_exists(model_id):
        raise HTTPException(status_code=404, detail="Model not found")
    
    if not request_data or 'ids' not in request_data:
        raise HTTPException(status_code=400, detail="ids parameter is required")
    
    ids = request_data['ids']
    if not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="ids must be a list")
    
    if len(ids) == 0:
        raise HTTPException(status_code=400, detail="ids list cannot be empty")
    
    try:
        db = get_db()
        
        # 1. 删除关联表中的记录
        placeholders = ','.join(['?' for _ in ids])
        db.execute(
            f'DELETE FROM cc_InstAsst_0_pub WHERE bk_obj_id = ? AND bk_inst_id IN ({placeholders})',
            [model_id] + ids
        )
        db.execute(
            f'DELETE FROM cc_InstAsst_0_pub WHERE bk_asst_obj_id = ? AND bk_asst_inst_id IN ({placeholders})',
            [model_id] + ids
        )
        
        # 2. 删除实例表中的记录
        result = db.execute(
            f'DELETE FROM "{table_name}" WHERE id IN ({placeholders})',
            ids
        )
        deleted_count = result.rowcount if hasattr(result, 'rowcount') else len(ids)
        
        print(f"[INFO] Deleted {deleted_count} instances from {table_name}")
        
        return {
            "deleted_count": deleted_count,
            "ids": ids,
            "message": f"Successfully deleted {deleted_count} instances"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    print(f"CMDB Server Lite - Starting on http://0.0.0.0:8000")
    print(f"Database: {DB_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
