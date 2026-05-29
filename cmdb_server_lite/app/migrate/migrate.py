
#!/usr/bin/env python3
"""
数据库初始化迁移工具
使用 sqlglot 处理多数据库方言
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
        "bk_property_name": "实例ID",
        "bk_property_type": "int",
        "isrequired": False,
        "isreadonly": True,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": False,
        "bk_isapi": False,
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
        "bk_property_name": "实例ID(BK)",
        "bk_property_type": "int",
        "isrequired": False,
        "isreadonly": True,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": False,
        "bk_isapi": False,
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
        "bk_isapi": True,
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
                INSERT INTO cc_ObjClassification
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
                    option TEXT,
                    bk_property_option TEXT,
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
                    ispre BOOLEAN DEFAULT false,
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
                    option = sys_prop.get("option")
                    if option and not isinstance(option, str):
                        option = json.dumps(option)
                    
                    self.execute_sql("""
                        INSERT INTO cc_ObjAttDes 
                        (_id, id, bk_obj_id, bk_property_id, bk_property_name, bk_property_type, 
                         bk_property_group, isrequired, bk_ispassword, bk_ishidden, isreadonly,
                         bk_isapi, bk_issystem, option, unit, placeholder, editable, ispre, 
                         bk_property_index, bk_supplier_account, bk_property_option)
                        VALUES (:_id, :id, :bk_obj_id, :bk_property_id, :bk_property_name, 
                                :bk_property_type, :bk_property_group, :isrequired, :bk_ispassword, 
                                :bk_ishidden, :isreadonly, :bk_isapi, :bk_issystem, :option, 
                                :unit, :placeholder, :editable, :ispre, :bk_property_index, 
                                '0', :bk_property_option)
                    """, {
                        '_id': f"{model_id}.{sys_prop['bk_property_id']}",
                        'id': attr_id,
                        'bk_obj_id': model_id,
                        'bk_property_id': sys_prop['bk_property_id'],
                        'bk_property_name': sys_prop['bk_property_name'],
                        'bk_property_type': sys_prop['bk_property_type'],
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
                        'bk_property_index': sys_prop['bk_property_index'],
                        'bk_property_option': option
                    })
                    attr_id += 1
                    total_attrs += 1
                
                # 再插入业务属性
                for prop in properties:
                    bk_property_id = prop.get("bk_property_id")
                    
                    if bk_property_id in SYSTEM_FIELDS:
                        continue
                    
                    option = prop.get("option")
                    if option and not isinstance(option, str):
                        option = json.dumps(option)
                    
                    bk_issystem = prop.get("bk_issystem", False)
                    bk_isapi = prop.get("bk_isapi", False)
                    isreadonly = prop.get("isreadonly", False)
                    editable = prop.get("editable", True)
                    bk_ishidden = prop.get("bk_ishidden", False)
                    
                    self.execute_sql("""
                        INSERT INTO cc_ObjAttDes 
                        (_id, id, bk_obj_id, bk_property_id, bk_property_name, bk_property_type, 
                         bk_property_group, isrequired, bk_ispassword, bk_ishidden, isreadonly,
                         bk_isapi, bk_issystem, option, unit, placeholder, editable, ispre, 
                         bk_property_index, bk_supplier_account, bk_property_option)
                        VALUES (:_id, :id, :bk_obj_id, :bk_property_id, :bk_property_name, 
                                :bk_property_type, :bk_property_group, :isrequired, :bk_ispassword, 
                                :bk_ishidden, :isreadonly, :bk_isapi, :bk_issystem, :option, 
                                :unit, :placeholder, :editable, :ispre, :bk_property_index, 
                                '0', :bk_property_option)
                    """, {
                        '_id': f"{model_id}.{bk_property_id}",
                        'id': attr_id,
                        'bk_obj_id': model_id,
                        'bk_property_id': bk_property_id,
                        'bk_property_name': prop.get("bk_property_name"),
                        'bk_property_type': prop.get("bk_property_type", "string"),
                        'bk_property_group': prop.get("bk_property_group", "default"),
                        'isrequired': prop.get("isrequired", False),
                        'bk_ispassword': prop.get("bk_ispassword", False),
                        'bk_ishidden': bk_ishidden,
                        'isreadonly': isreadonly,
                        'bk_isapi': bk_isapi,
                        'bk_issystem': bk_issystem,
                        'option': option,
                        'unit': prop.get("unit"),
                        'placeholder': prop.get("placeholder"),
                        'editable': editable,
                        'ispre': prop.get("ispre", False),
                        'bk_property_index': prop.get("bk_property_index", 0),
                        'bk_property_option': option
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
        
        # 步骤5: 创建实例表
        models = self.execute_query("SELECT bk_obj_id FROM cc_ObjDes")
        for model in models:
            self.create_instance_table(model['bk_obj_id'])
        
        # 步骤6: 迁移实例数据
        self.migrate_instances()
        
        logger.info("数据库初始化迁移完成!")


if __name__ == "__main__":
    # 直接运行迁移
    migrator = DatabaseMigrator()
    migrator.migrate()
