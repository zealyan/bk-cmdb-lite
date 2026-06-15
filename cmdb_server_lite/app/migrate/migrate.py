
#!/usr/bin/env python3
"""
数据库初始化迁移工具
使用 sqlglot 处理多数据库方言

枚举选项格式（原项目标准格式）：
- enum（单选枚举）: [{"id": "xxx", "name": "显示名", "type": "text", "is_default": false}]
- enummulti（多选枚举）: [{"id": "xxx", "name": "显示名", "type": "text", "is_default": false}]
- list（列表）: ["选项1", "选项2"]
- int: {"min": 0, "max": 100}
- float: {"min": 0.0, "max": 100.5}
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
import coloredlogs
import logging
from sqlglot import parse_one, transpile
from sqlalchemy import text
from app.db.engine import get_connection
from app.config.settings import get_config


# 配置日志
logger = logging.getLogger('migrate')
coloredlogs.install(level='INFO', logger=logger)


def convert_enum_option(option_list, default_index=None):
    """
    将简单的字符串数组格式转换为原项目标准的枚举选项格式
    
    Args:
        option_list: 简单字符串数组，如 ["选项1", "选项2", "选项3"]
        default_index: 默认选中的索引（可选），从0开始
    
    Returns:
        JSON字符串，符合原项目EnumVal格式
    """
    if not option_list:
        return None
    
    enum_options = []
    for idx, option_text in enumerate(option_list):
        # 使用字符串本身作为ID（URL安全）
        option_id = str(option_text).strip()
        enum_options.append({
            "id": option_id,
            "name": str(option_text).strip(),
            "type": "text",
            "is_default": True if default_index is not None and idx == default_index else False
        })
    
    return json.dumps(enum_options, ensure_ascii=False)


def parse_enum_option(json_string):
    """
    解析JSON字符串为枚举选项列表
    
    Args:
        json_string: JSON格式的枚举选项字符串
    
    Returns:
        枚举选项列表
    """
    if not json_string:
        return []
    
    if isinstance(json_string, list):
        return json_string
    
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return []

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

# 系统属性定义
SYSTEM_PROPERTIES = [
    {
        "bk_property_id": "id",
        "bk_property_name": "数据ID",
        "bk_property_type": "int",
        "isrequired": False,
        "isreadonly": True,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": False,
        "bk_isapi": True,   # 内部数据库字段，与原项目保持一致：设置为API字段，在表单和搜索中过滤
        "bk_issystem": True,
        "ispre": True,
        "bk_property_index": -1,
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    },
    {
        "bk_property_id": "bk_inst_id",
        "bk_property_name": "实例ID",
        "bk_property_type": "int",
        "isrequired": False,
        "isreadonly": True,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": False,
        "bk_isapi": True,  # 与原项目保持一致：设置为API字段，在表单和搜索中过滤
        "bk_issystem": True,
        "ispre": True,
        "bk_property_index": 0,
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    },
    {
        "bk_property_id": "bk_inst_name",
        "bk_property_name": "实例名称",
        "bk_property_type": "string",
        "isrequired": True,
        "isreadonly": False,
        "editable": True,
        "bk_ispassword": False,
        "bk_ishidden": False,
        "bk_isapi": False,
        "bk_issystem": True,
        "ispre": True,
        "bk_property_index": 1,
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    },
    {
        "bk_property_id": "bk_obj_id",
        "bk_property_name": "模型ID",
        "bk_property_type": "string",
        "isrequired": True,
        "isreadonly": True,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": True,
        "bk_isapi": True,
        "bk_issystem": True,
        "ispre": True,
        "bk_property_index": 2,
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    }
]

# 模型分类映射
MODEL_CLASSIFICATION_MAP = {
    "bk_switch": "bk_network",
    "bk_host": "bk_host_manage",
    "bk_slb": "bk_loadbalance",
    "bk_slb_server": "bk_loadbalance",
    "bk_slb_listener": "bk_loadbalance",
}

# 分类定义
CLASSIFICATIONS = [
    {"id": 1, "bk_classification_id": "bk_network", "bk_classification_name": "网络", "bk_classification_icon": "icon-cc-network", "ispre": True},
    {"id": 2, "bk_classification_id": "bk_host_manage", "bk_classification_name": "主机管理", "bk_classification_icon": "icon-cc-host", "ispre": True},
    {"id": 3, "bk_classification_id": "bk_loadbalance", "bk_classification_name": "负载均衡", "bk_classification_icon": "icon-cc-loadbalance", "ispre": True},
]

# 属性分组定义
PROPERTY_GROUPS = [
    {"id": 1, "bk_group_id": "default", "bk_group_name": "默认", "bk_isdefault": True, "is_collapse": False, "ispre": True, "bk_group_index": 0},
    {"id": 2, "bk_group_id": "base", "bk_group_name": "基础信息", "bk_isdefault": False, "is_collapse": False, "ispre": True, "bk_group_index": 1},
]

# 需要更新分组的属性映射（属性ID -> 分组ID）
PROPERTY_GROUP_UPDATE_MAP = {
    "name": "base",
    "bk_inst_name": "base",
    "bk_host_innerip": "base",
    "bk_host_outerip": "base",
    "bk_cloud_id": "base",
    "bk_switch_name": "base",
    "bk_switch_ip": "base",
    "bk_lb_name": "base",
    "bk_server_name": "base",
    "bk_listener_name": "base",
    "description": "base",
}


class DatabaseMigrator:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.project_root = Path(__file__).parent.parent.parent
        self.workspace_root = self.project_root.parent
        
    def execute_sql(self, sql, params=None):
        """执行 SQL 语句"""
        conn = get_connection()
        try:
            if params:
                conn.execute(text(sql), params)
            else:
                conn.execute(text(sql))
            conn.commit()
        finally:
            conn.close()
    
    def execute_query(self, sql, params=None):
        """执行查询并返回结果"""
        conn = get_connection()
        try:
            if params:
                result = conn.execute(text(sql), params)
            else:
                result = conn.execute(text(sql))
            # 转换为字典列表
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result]
        finally:
            conn.close()
    
    def migrate_classifications(self):
        """迁移分类数据"""
        for cls in CLASSIFICATIONS:
            self.execute_sql("""
                INSERT OR REPLACE INTO cc_ObjClassification
                (id, bk_classification_id, bk_classification_name, bk_classification_icon, ispre, bk_supplier_account)
                VALUES (:id, :bk_classification_id, :bk_classification_name, :bk_classification_icon, :ispre, '0')
            """, {
                "id": cls["id"],
                "bk_classification_id": cls["bk_classification_id"],
                "bk_classification_name": cls["bk_classification_name"],
                "bk_classification_icon": cls["bk_classification_icon"],
                "ispre": cls["ispre"]
            })
        logger.info(f"迁移 {len(CLASSIFICATIONS)} 个分类")
    
    def migrate_property_groups(self):
        """迁移属性分组数据"""
        # 先获取所有模型
        models = self.execute_query("SELECT bk_obj_id FROM cc_ObjDes")
        
        group_id = 1
        for model in models:
            model_id = model['bk_obj_id']
            for group in PROPERTY_GROUPS:
                self.execute_sql("""
                    INSERT OR REPLACE INTO cc_PropertyGroup
                    (_id, id, bk_obj_id, bk_group_id, bk_group_name, bk_group_index, 
                     bk_isdefault, is_collapse, ispre, bk_biz_id, bk_supplier_account,
                     creator, modifier)
                    VALUES (:_id, :id, :bk_obj_id, :bk_group_id, :bk_group_name, 
                            :bk_group_index, :bk_isdefault, :is_collapse, :ispre,
                            0, '0', 'admin', 'admin')
                """, {
                    '_id': f"{model_id}.{group['bk_group_id']}",
                    'id': group_id,
                    'bk_obj_id': model_id,
                    'bk_group_id': group['bk_group_id'],
                    'bk_group_name': group['bk_group_name'],
                    'bk_group_index': group['bk_group_index'],
                    'bk_isdefault': group['bk_isdefault'],
                    'is_collapse': group['is_collapse'],
                    'ispre': group['ispre']
                })
                group_id += 1
        
        logger.info(f"迁移了 {len(models) * len(PROPERTY_GROUPS)} 个属性分组")
    
    def update_attributes_group(self):
        """更新现有属性的分组"""
        # 构建 CASE WHEN 语句
        case_when_clauses = []
        params = {}
        
        for idx, (prop_id, group_id) in enumerate(PROPERTY_GROUP_UPDATE_MAP.items()):
            param_name = f"prop_{idx}"
            param_group = f"group_{idx}"
            case_when_clauses.append(f"WHEN bk_property_id = :{param_name} THEN :{param_group}")
            params[param_name] = prop_id
            params[param_group] = group_id
        
        if case_when_clauses:
            sql = f"""
                UPDATE cc_ObjAttDes 
                SET bk_property_group = CASE 
                    {' '.join(case_when_clauses)}
                    ELSE bk_property_group
                END
                WHERE bk_property_id IN ({', '.join([f':prop_{i}' for i in range(len(PROPERTY_GROUP_UPDATE_MAP))])})
            """
            
            # 执行更新
            self.execute_sql(sql, params)
            
            updated_count = len(PROPERTY_GROUP_UPDATE_MAP)
            logger.info(f"更新了 {updated_count} 个属性的分组")
    
    def init_core_tables(self):
        """初始化核心表结构"""
        core_tables_sql = {
            "cc_ObjClassification": """
                CREATE TABLE IF NOT EXISTS cc_ObjClassification (
                    id INTEGER PRIMARY KEY,
                    bk_classification_id VARCHAR NOT NULL UNIQUE,
                    bk_classification_name VARCHAR NOT NULL,
                    bk_classification_icon VARCHAR,
                    ispre BOOLEAN DEFAULT false,
                    bk_supplier_account VARCHAR DEFAULT '0'
                )
            """,
            "cc_ObjDes": """
                CREATE TABLE IF NOT EXISTS cc_ObjDes (
                    _id VARCHAR,
                    id INTEGER,
                    bk_obj_id VARCHAR NOT NULL PRIMARY KEY,
                    bk_obj_name VARCHAR NOT NULL,
                    bk_obj_icon VARCHAR,
                    bk_classification_id VARCHAR,
                    ispre BOOLEAN DEFAULT false,
                    bk_ishidden BOOLEAN DEFAULT false,
                    bk_ispaused BOOLEAN DEFAULT false,
                    obj_sort_number INTEGER DEFAULT 0,
                    creator VARCHAR DEFAULT 'admin',
                    modifier VARCHAR DEFAULT 'admin',
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bk_supplier_account VARCHAR DEFAULT '0'
                )
            """,
            "cc_PropertyGroup": """
                CREATE TABLE IF NOT EXISTS cc_PropertyGroup (
                    _id VARCHAR,
                    id INTEGER PRIMARY KEY,
                    bk_obj_id VARCHAR,
                    bk_group_id VARCHAR NOT NULL,
                    bk_group_name VARCHAR NOT NULL,
                    bk_group_index INTEGER DEFAULT 0,
                    bk_isdefault BOOLEAN DEFAULT false,
                    is_collapse BOOLEAN DEFAULT false,
                    ispre BOOLEAN DEFAULT false,
                    bk_biz_id INTEGER DEFAULT 0,
                    creator VARCHAR DEFAULT 'admin',
                    modifier VARCHAR DEFAULT 'admin',
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bk_supplier_account VARCHAR DEFAULT '0'
                )
            """,
            "cc_ObjAttDes": """
                CREATE TABLE IF NOT EXISTS cc_ObjAttDes (
                    _id VARCHAR,
                    id INTEGER,
                    bk_obj_id VARCHAR NOT NULL,
                    bk_property_id VARCHAR NOT NULL,
                    bk_property_name VARCHAR NOT NULL,
                    bk_property_type VARCHAR NOT NULL,
                    bk_property_group VARCHAR DEFAULT 'default',
                    isrequired BOOLEAN DEFAULT false,
                    bk_ispassword BOOLEAN DEFAULT false,
                    bk_ishidden BOOLEAN DEFAULT false,
                    isreadonly BOOLEAN DEFAULT false,
                    editable BOOLEAN DEFAULT true,
                    bk_isapi BOOLEAN DEFAULT false,
                    bk_issystem BOOLEAN DEFAULT false,
                    ispre BOOLEAN DEFAULT false,
                    bk_property_index INTEGER DEFAULT 0,
                    ismultiple BOOLEAN DEFAULT false,
                    option TEXT,
                    placeholder VARCHAR,
                    unit VARCHAR,
                    creator VARCHAR DEFAULT 'admin',
                    modifier VARCHAR DEFAULT 'admin',
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bk_supplier_account VARCHAR DEFAULT '0',
                    PRIMARY KEY (bk_obj_id, bk_property_id)
                )
            """,
            "cc_AsstDes": """
                CREATE TABLE IF NOT EXISTS cc_AsstDes (
                    _id VARCHAR,
                    id INTEGER,
                    bk_asst_id VARCHAR NOT NULL PRIMARY KEY,
                    bk_asst_name VARCHAR NOT NULL,
                    bk_asst_icon VARCHAR,
                    src_des VARCHAR DEFAULT '',
                    dest_des VARCHAR DEFAULT '',
                    direction VARCHAR DEFAULT 'forward',
                    ispre BOOLEAN DEFAULT false,
                    creator VARCHAR DEFAULT 'admin',
                    modifier VARCHAR DEFAULT 'admin',
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bk_supplier_account VARCHAR DEFAULT '0'
                )
            """,
            "cc_ObjAsst": """
                CREATE TABLE IF NOT EXISTS cc_ObjAsst (
                    _id VARCHAR,
                    id INTEGER,
                    bk_obj_id VARCHAR NOT NULL,
                    target_obj_id VARCHAR NOT NULL,
                    target_obj_name VARCHAR NOT NULL,
                    bk_asst_id VARCHAR NOT NULL,
                    bk_obj_asst_id VARCHAR NOT NULL PRIMARY KEY,
                    bk_obj_asst_name VARCHAR NOT NULL,
                    mapping VARCHAR,
                    on_delete VARCHAR,
                    creator VARCHAR DEFAULT 'admin',
                    modifier VARCHAR DEFAULT 'admin',
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bk_supplier_account VARCHAR DEFAULT '0'
                )
            """,
            "cc_InstAsst_0_pub": """
                CREATE TABLE IF NOT EXISTS cc_InstAsst_0_pub (
                    _id VARCHAR,
                    id INTEGER PRIMARY KEY,
                    bk_obj_id VARCHAR NOT NULL,
                    bk_inst_id INTEGER NOT NULL,
                    bk_asst_obj_id VARCHAR NOT NULL,
                    bk_asst_inst_id INTEGER NOT NULL,
                    bk_obj_asst_id VARCHAR NOT NULL,
                    bk_relation_type_id VARCHAR NOT NULL,
                    bk_supplier_account VARCHAR DEFAULT '0'
                )
            """,
            "user_custom": """
                CREATE TABLE IF NOT EXISTS user_custom (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name VARCHAR NOT NULL,
                    config_key VARCHAR NOT NULL,
                    config_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_name, config_key)
                )
            """,
        }
        
        for table_name, create_sql in core_tables_sql.items():
            self.execute_sql(create_sql)
            logger.info(f"初始化核心表: {table_name}")
    
    def migrate_models(self):
        """迁移模型数据"""
        ui_project = self.workspace_root / "cmdb_ui_lite" / "src" / "assets" / "api"
        index_path = ui_project / "index.json"
        
        if not index_path.exists():
            logger.warning(f"找不到模型数据文件: {index_path}")
            return
        
        with open(index_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for idx, model in enumerate(data.get("models", [])):
            model_id = model.get("bk_obj_id")
            classification_id = MODEL_CLASSIFICATION_MAP.get(model_id, "bk_uncategorized")
            
            self.execute_sql("""
                INSERT OR REPLACE INTO cc_ObjDes 
                (_id, id, bk_obj_id, bk_obj_name, bk_obj_icon, bk_classification_id, ispre,
                 bk_supplier_account, creator, modifier, obj_sort_number)
                VALUES (:_id, :id, :bk_obj_id, :bk_obj_name, :bk_obj_icon, :bk_classification_id,
                        :ispre, '0', 'admin', 'admin', :obj_sort_number)
            """, {
                '_id': model_id,
                'id': idx + 1,
                'bk_obj_id': model_id,
                'bk_obj_name': model.get("bk_obj_name"),
                'bk_obj_icon': model.get("bk_obj_icon"),
                'bk_classification_id': classification_id,
                'ispre': True,
                'obj_sort_number': idx
            })
        
        logger.info(f"迁移了 {len(data.get('models', []))} 个模型")
    
    def process_option(self, prop_type, option):
        """
        处理属性选项值，根据类型进行转换
        
        Args:
            prop_type: 属性类型
            option: 原始选项值
        
        Returns:
            处理后的选项值（JSON字符串或原值）
        """
        if option is None:
            return None
        
        # 如果已经是字符串，直接返回
        if isinstance(option, str):
            return option
        
        # 枚举类型（单选）
        if prop_type == 'enum':
            if isinstance(option, list):
                # 将简单数组转换为原项目标准格式
                return convert_enum_option(option)
            return option
        
        # 多选枚举类型
        if prop_type == 'enummulti':
            if isinstance(option, list):
                # 将简单数组转换为原项目标准格式
                return convert_enum_option(option)
            return option
        
        # 列表类型
        if prop_type == 'list':
            if isinstance(option, list):
                return json.dumps(option, ensure_ascii=False)
            return option
        
        # 整数范围类型
        if prop_type == 'int':
            if isinstance(option, dict):
                return json.dumps(option, ensure_ascii=False)
            return option
        
        # 浮点数范围类型
        if prop_type == 'float':
            if isinstance(option, dict):
                return json.dumps(option, ensure_ascii=False)
            return option
        
        # 其他类型转为JSON字符串
        return json.dumps(option, ensure_ascii=False)
    
    def migrate_attributes(self):
        """迁移属性数据"""
        ui_project = self.workspace_root / "cmdb_ui_lite" / "src" / "assets" / "api"
        index_path = ui_project / "index.json"
        
        if not index_path.exists():
            logger.warning(f"找不到模型数据文件: {index_path}")
            return
        
        with open(index_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        attr_id = 1
        total_attrs = 0
        
        for model in data.get("models", []):
            model_id = model.get("bk_obj_id")
            attr_file_path = ui_project / "models" / "attributes" / f"{model_id}.json"
            
            try:
                with open(attr_file_path, 'r', encoding='utf-8') as f:
                    attr_data = json.load(f)
                
                properties = attr_data.get("info", [])
                
                logger.info(f"插入模型 {model_id} 的 {len(SYSTEM_PROPERTIES)} 个系统属性")
                
                # 先插入系统属性
                for sys_prop in SYSTEM_PROPERTIES:
                    prop_type = sys_prop.get("bk_property_type", "string")
                    option = sys_prop.get("option")
                    option = self.process_option(prop_type, option)
                    
                    self.execute_sql("""
                        INSERT INTO cc_ObjAttDes 
                        (_id, id, bk_obj_id, bk_property_id, bk_property_name, bk_property_type, 
                         bk_property_group, isrequired, bk_ispassword, bk_ishidden, isreadonly,
                         bk_isapi, bk_issystem, option, unit, placeholder, editable, ispre, 
                         bk_property_index, bk_supplier_account)
                        VALUES (:_id, :id, :bk_obj_id, :bk_property_id, :bk_property_name, 
                                :bk_property_type, :bk_property_group, :isrequired, :bk_ispassword, 
                                :bk_ishidden, :isreadonly, :bk_isapi, :bk_issystem, :option, 
                                :unit, :placeholder, :editable, :ispre, :bk_property_index, '0')
                    """, {
                        '_id': f"{model_id}.{sys_prop['bk_property_id']}",
                        'id': attr_id,
                        'bk_obj_id': model_id,
                        'bk_property_id': sys_prop['bk_property_id'],
                        'bk_property_name': sys_prop['bk_property_name'],
                        'bk_property_type': prop_type,
                        'bk_property_group': sys_prop['bk_property_group'],
                        'isrequired': sys_prop['isrequired'],
                        'bk_ispassword': sys_prop['bk_ispassword'],
                        'bk_ishidden': sys_prop['bk_ishidden'],
                        'isreadonly': sys_prop['isreadonly'],
                        'bk_isapi': sys_prop['bk_isapi'],
                        'bk_issystem': sys_prop['bk_issystem'],
                        'option': option,
                        'unit': sys_prop['unit'],
                        'placeholder': sys_prop['placeholder'],
                        'editable': sys_prop['editable'],
                        'ispre': sys_prop['ispre'],
                        'bk_property_index': sys_prop['bk_property_index']
                    })
                    attr_id += 1
                    total_attrs += 1
                
                # 再插入业务属性
                for prop in properties:
                    bk_property_id = prop.get("bk_property_id")
                    
                    if bk_property_id in SYSTEM_FIELDS:
                        continue
                    
                    prop_type = prop.get("bk_property_type", "string")
                    option = prop.get("option")
                    option = self.process_option(prop_type, option)
                    
                    # 判断是否为多选枚举
                    is_multiple = prop_type == 'enummulti'
                    
                    bk_issystem = prop.get("bk_issystem", False)
                    bk_isapi = prop.get("bk_isapi", False)
                    isreadonly = prop.get("isreadonly", False)
                    editable = prop.get("editable", True)
                    bk_ishidden = prop.get("bk_ishidden", False)
                    
                    self.execute_sql("""
                        INSERT INTO cc_ObjAttDes 
                        (_id, id, bk_obj_id, bk_property_id, bk_property_name, bk_property_type, 
                         bk_property_group, isrequired, bk_ispassword, bk_ishidden, isreadonly,
                         bk_isapi, bk_issystem, ismultiple, option, unit, placeholder, editable, ispre, 
                         bk_property_index, bk_supplier_account)
                        VALUES (:_id, :id, :bk_obj_id, :bk_property_id, :bk_property_name, 
                                :bk_property_type, :bk_property_group, :isrequired, :bk_ispassword, 
                                :bk_ishidden, :isreadonly, :bk_isapi, :bk_issystem, :ismultiple, :option, 
                                :unit, :placeholder, :editable, :ispre, :bk_property_index, '0')
                    """, {
                        '_id': f"{model_id}.{bk_property_id}",
                        'id': attr_id,
                        'bk_obj_id': model_id,
                        'bk_property_id': bk_property_id,
                        'bk_property_name': prop.get("bk_property_name"),
                        'bk_property_type': prop_type,
                        'bk_property_group': prop.get("bk_property_group", "default"),
                        'isrequired': prop.get("isrequired", False),
                        'bk_ispassword': prop.get("bk_ispassword", False),
                        'bk_ishidden': bk_ishidden,
                        'isreadonly': isreadonly,
                        'bk_isapi': bk_isapi,
                        'bk_issystem': bk_issystem,
                        'ismultiple': is_multiple,
                        'option': option,
                        'unit': prop.get("unit"),
                        'placeholder': prop.get("placeholder"),
                        'editable': editable,
                        'ispre': prop.get("ispre", False),
                        'bk_property_index': prop.get("bk_property_index", 0)
                    })
                    attr_id += 1
                    total_attrs += 1
                
                logger.info(f"迁移模型 {model_id} 的 {len(properties) + len(SYSTEM_PROPERTIES)} 个属性")
            except FileNotFoundError:
                logger.warning(f"警告：未找到属性文件 {attr_file_path}")
        
        logger.info(f"总共迁移 {total_attrs} 个属性")
    
    def create_instance_table(self, model_id):
        """为模型创建实例表"""
        table_name = f"cc_ObjectBase_0_pub_{model_id}"
        
        # 先查询模型的属性定义
        attributes = self.execute_query("""
            SELECT bk_property_id, bk_property_type
            FROM cc_ObjAttDes 
            WHERE bk_obj_id = :model_id AND bk_property_id NOT IN ('id', 'bk_inst_id', 'bk_inst_name', 'bk_obj_id')
            ORDER BY bk_property_index
        """, {"model_id": model_id})
        
        # 构建表结构
        columns = [
            '_id VARCHAR',
            'id INTEGER PRIMARY KEY',
            'bk_inst_id INTEGER NOT NULL',
            'bk_inst_name VARCHAR NOT NULL',
            'bk_supplier_account VARCHAR DEFAULT \'0\'',
            'bk_obj_id VARCHAR NOT NULL',
            'create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'bk_operate_time TIMESTAMP'
        ]
        
        # 添加模型自定义属性
        for attr in attributes:
            prop_id = attr['bk_property_id']
            prop_type = attr['bk_property_type']
            
            if prop_id in SYSTEM_FIELDS:
                continue
            
            sql_type = self.get_sql_type(prop_type)
            columns.append(f'"{prop_id}" {sql_type}')
        
        create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(columns)})'
        self.execute_sql(create_sql)
        logger.info(f"创建实例表: {table_name}")
    
    def get_sql_type(self, prop_type):
        """获取属性类型对应的 SQL 类型"""
        type_mapping = {
            'int': 'INTEGER',
            'long': 'BIGINT',
            'string': 'TEXT',
            'char': 'VARCHAR',
            'float': 'FLOAT',
            'double': 'DOUBLE',
            'date': 'DATE',
            'time': 'TIME',
            'datetime': 'TIMESTAMP',
            'bool': 'BOOLEAN',
            'boolean': 'BOOLEAN',
            'objuser': 'TEXT',
            'list': 'TEXT',
            'enum': 'TEXT',
            'enummulti': 'TEXT',
            'enumquote': 'TEXT',
            'textarea': 'TEXT',
            'array': 'TEXT',
            'object': 'TEXT'
        }
        return type_mapping.get(prop_type, 'TEXT')
    
    def migrate_instances(self):
        """迁移实例数据"""
        ui_project = self.workspace_root / "cmdb_ui_lite" / "src" / "assets" / "api"
        
        with open(ui_project / "index.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for model in data["models"]:
            model_id = model.get("bk_obj_id")
            table_name = f"cc_ObjectBase_0_pub_{model_id}"
            inst_file_path = ui_project / "models" / "instances" / f"{model_id}.json"
            
            try:
                with open(inst_file_path, 'r', encoding='utf-8') as f:
                    inst_data = json.load(f)
                
                instances = inst_data.get("info", [])
                
                # 先获取模型的属性定义，用于正确处理数据类型
                attributes = self.execute_query("""
                    SELECT bk_property_id, bk_property_type FROM cc_ObjAttDes WHERE bk_obj_id = :model_id
                """, {"model_id": model_id})
                attr_type_map = {
                    attr['bk_property_id']: attr['bk_property_type']
                    for attr in attributes
                }
                
                logger.info(f"迁移模型 {model_id} 的 {len(instances)} 个实例")
                
                for idx, inst in enumerate(instances):
                    columns = []
                    placeholders = []
                    values = []
                    
                    inst_id = inst.get("id", idx + 1)
                    bk_inst_id = inst.get("bk_inst_id", inst_id)
                    bk_inst_name = inst.get("bk_inst_name", "")
                    
                    if not bk_inst_name and "name" in inst:
                        bk_inst_name = inst["name"]
                    elif not bk_inst_name and "bk_lb_name" in inst:
                        bk_inst_name = inst["bk_lb_name"]
                    elif not bk_inst_name and "bk_host_innerip" in inst:
                        bk_inst_name = inst["bk_host_innerip"]
                    elif not bk_inst_name and "bk_server_name" in inst:
                        bk_inst_name = inst["bk_server_name"]
                    elif not bk_inst_name and "bk_listener_name" in inst:
                        bk_inst_name = inst["bk_listener_name"]
                    elif not bk_inst_name and "bk_switch_name" in inst:
                        bk_inst_name = inst["bk_switch_name"]
                    
                    # 添加必要字段
                    if inst_id:
                        columns.append("id")
                        placeholders.append(":id")
                        values.append(inst_id)
                    if bk_inst_id:
                        columns.append("bk_inst_id")
                        placeholders.append(":bk_inst_id")
                        values.append(bk_inst_id)
                    if bk_inst_name:
                        columns.append("bk_inst_name")
                        placeholders.append(":bk_inst_name")
                        values.append(bk_inst_name)
                    
                    # 添加其他字段
                    for key, value in inst.items():
                        if key not in ["id", "bk_inst_id", "bk_inst_name"]:
                            columns.append(f'"{key}"')
                            placeholders.append(f":{key}")
                            # 根据属性类型处理值
                            prop_type = attr_type_map.get(key)
                            if prop_type in ['list', 'enum', 'enummulti', 'array', 'object'] and isinstance(value, (list, dict)):
                                values.append(json.dumps(value, ensure_ascii=False))
                            else:
                                values.append(value)
                    
                    if columns:
                        columns.append("bk_obj_id")
                        placeholders.append(":bk_obj_id")
                        values.append(model_id)
                        
                        columns.append("bk_supplier_account")
                        placeholders.append(":bk_supplier_account")
                        values.append("0")
                        
                        # 构建参数字典
                        params = {}
                        for col, val in zip([c.strip('"') for c in columns], values):
                            params[col] = val
                        
                        sql = f'INSERT OR REPLACE INTO "{table_name}" ({", ".join(columns)}) VALUES ({", ".join(placeholders)})'
                        self.execute_sql(sql, params)
                
            except FileNotFoundError:
                logger.warning(f"未找到实例文件 {inst_file_path}")
    
    def migrate_associations(self):
        """迁移关联关系数据"""
        ui_project = self.workspace_root / "cmdb_ui_lite" / "src" / "assets" / "api"

        # 1. 先添加原项目标准关联类型到 cc_AsstDes
        # 原项目 bk_asst_id 标准值（来自 definitions.go）:
        # - bk_mainline: 主线关联
        # - belong: 属于
        # - group: 分组
        # - run: 运行
        # - connect: 连接
        # - default: 默认
        asst_types = [
            {
                "bk_asst_id": "default",
                "bk_asst_name": "默认",
                "src_des": "指向",
                "dest_des": "被指向",
                "direction": "forward",
                "bk_supplier_account": "0",
                "ispre": True
            },
            {
                "bk_asst_id": "belong",
                "bk_asst_name": "属于",
                "src_des": "属于",
                "dest_des": "包含",
                "direction": "forward",
                "bk_supplier_account": "0",
                "ispre": True
            },
            {
                "bk_asst_id": "connect",
                "bk_asst_name": "连接",
                "src_des": "连接",
                "dest_des": "被连接",
                "direction": "forward",
                "bk_supplier_account": "0",
                "ispre": True
            },
            {
                "bk_asst_id": "group",
                "bk_asst_name": "分组",
                "src_des": "分组",
                "dest_des": "被分组",
                "direction": "forward",
                "bk_supplier_account": "0",
                "ispre": True
            },
            {
                "bk_asst_id": "run",
                "bk_asst_name": "运行",
                "src_des": "运行于",
                "dest_des": "运行",
                "direction": "forward",
                "bk_supplier_account": "0",
                "ispre": True
            },
        ]

        for idx, asst_type in enumerate(asst_types, 1):
            self.execute_sql("""
                INSERT OR REPLACE INTO cc_AsstDes 
                (id, bk_asst_id, bk_asst_name, src_des, dest_des, direction, ispre, bk_supplier_account, creator, modifier)
                VALUES (:id, :bk_asst_id, :bk_asst_name, :src_des, :dest_des, :direction, :ispre, :bk_supplier_account, 'admin', 'admin')
            """, {
                "id": idx,
                "bk_asst_id": asst_type["bk_asst_id"],
                "bk_asst_name": asst_type["bk_asst_name"],
                "src_des": asst_type["src_des"],
                "dest_des": asst_type["dest_des"],
                "direction": asst_type["direction"],
                "ispre": asst_type["ispre"],
                "bk_supplier_account": asst_type["bk_supplier_account"]
            })
        
        logger.info(f"迁移了 {len(asst_types)} 个关联类型")

        # 2. 添加对象关联到 cc_ObjAsst
        # bk_obj_asst_id 格式: {源模型ID}_{AsstKindID}_{目标模型ID}
        # 例如: bk_slb_default_bk_slb_server = bk_slb + default + bk_slb_server
        obj_associations = [
            {
                "bk_obj_id": "bk_slb",
                "target_obj_id": "bk_slb_server",
                "target_obj_name": "后端服务器",
                "bk_asst_id": "default",  # 使用标准关联类型
                "bk_obj_asst_id": "bk_slb_default_bk_slb_server",  # {源}_{类型}_{目标}
                "bk_obj_asst_name": "指向后端服务器",
                "bk_supplier_account": "0",
                "mapping": None,
                "on_delete": None
            },
            {
                "bk_obj_id": "bk_slb",
                "target_obj_id": "bk_slb_listener",
                "target_obj_name": "监听器",
                "bk_asst_id": "default",  # 使用标准关联类型
                "bk_obj_asst_id": "bk_slb_default_bk_slb_listener",  # {源}_{类型}_{目标}
                "bk_obj_asst_name": "指向监听器",
                "bk_supplier_account": "0",
                "mapping": None,
                "on_delete": None
            }
        ]

        for idx, obj_asst in enumerate(obj_associations, 1):
            self.execute_sql("""
                INSERT OR REPLACE INTO cc_ObjAsst 
                (id, bk_obj_id, target_obj_id, target_obj_name, bk_asst_id, 
                 bk_obj_asst_id, bk_obj_asst_name, mapping, on_delete, 
                 creator, modifier, bk_supplier_account)
                VALUES (:id, :bk_obj_id, :target_obj_id, :target_obj_name, :bk_asst_id, 
                        :bk_obj_asst_id, :bk_obj_asst_name, :mapping, :on_delete, 
                        'admin', 'admin', :bk_supplier_account)
            """, {
                "id": idx,
                "bk_obj_id": obj_asst["bk_obj_id"],
                "target_obj_id": obj_asst["target_obj_id"],
                "target_obj_name": obj_asst["target_obj_name"],
                "bk_asst_id": obj_asst["bk_asst_id"],
                "bk_obj_asst_id": obj_asst["bk_obj_asst_id"],
                "bk_obj_asst_name": obj_asst["bk_obj_asst_name"],
                "mapping": obj_asst["mapping"],
                "on_delete": obj_asst["on_delete"],
                "bk_supplier_account": obj_asst["bk_supplier_account"]
            })
        
        logger.info(f"迁移了 {len(obj_associations)} 个对象关联")

        # 3. 迁移实例关联数据
        inst_assoc_file = ui_project / "models" / "associations" / "index.json"
        if inst_assoc_file.exists():
            with open(inst_assoc_file, 'r', encoding='utf-8') as f:
                inst_assoc_data = json.load(f)
            
            associations = inst_assoc_data.get("associations", [])
            
            for assoc in associations:
                # 确定 bk_obj_asst_id 和 bk_relation_type_id
                # 格式: {源模型ID}_{AsstKindID}_{目标模型ID}
                # 例如: bk_slb_default_bk_slb_server
                bk_obj_id = assoc.get("bk_obj_id")
                bk_asst_obj_id = assoc.get("bk_asst_obj_id")
                # bk_relation_type_id 现在使用标准 bk_asst_id (default)
                bk_relation_type_id = assoc.get("bk_relation_type_id")
                # bk_obj_asst_id 格式: {源}_{类型}_{目标}
                bk_obj_asst_id = f"{bk_obj_id}_{bk_relation_type_id}_{bk_asst_obj_id}"
                
                self.execute_sql("""
                    INSERT OR REPLACE INTO cc_InstAsst_0_pub 
                    (id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id, 
                     bk_obj_asst_id, bk_relation_type_id, bk_supplier_account)
                    VALUES (:id, :bk_obj_id, :bk_inst_id, :bk_asst_obj_id, :bk_asst_inst_id, 
                            :bk_obj_asst_id, :bk_relation_type_id, :bk_supplier_account)
                """, {
                    "id": assoc.get("id"),
                    "bk_obj_id": bk_obj_id,
                    "bk_inst_id": assoc.get("bk_inst_id"),
                    "bk_asst_obj_id": bk_asst_obj_id,
                    "bk_asst_inst_id": assoc.get("bk_asst_inst_id"),
                    "bk_obj_asst_id": bk_obj_asst_id,
                    "bk_relation_type_id": assoc.get("bk_relation_type_id"),
                    "bk_supplier_account": "0"
                })
            
            logger.info(f"迁移了 {len(associations)} 个实例关联")
        else:
            logger.warning("未找到实例关联数据文件")

    def migrate(self):
        """执行完整的迁移"""
        logger.info("开始数据库初始化迁移...")

        # 步骤1: 初始化核心表
        self.init_core_tables()

        # 步骤2: 迁移分类
        self.migrate_classifications()

        # 步骤3: 迁移模型
        self.migrate_models()

        # 步骤4: 迁移属性
        self.migrate_attributes()

        # 步骤5: 迁移属性分组
        self.migrate_property_groups()

        # 步骤6: 更新属性分组
        self.update_attributes_group()

        # 步骤7: 创建实例表
        models = self.execute_query("SELECT bk_obj_id FROM cc_ObjDes")
        for model in models:
            self.create_instance_table(model['bk_obj_id'])

        # 步骤8: 迁移实例数据
        self.migrate_instances()

        # 步骤9: 迁移关联关系数据
        self.migrate_associations()

        logger.info("数据库初始化迁移完成!")


if __name__ == "__main__":
    # 直接运行迁移
    migrator = DatabaseMigrator()
    migrator.migrate()
