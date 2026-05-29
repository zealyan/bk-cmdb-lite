#!/usr/bin/env python3
"""
数据库初始化迁移工具
使用 sqlglot 处理多数据库方言
"""

import json
import os
from pathlib import Path
from datetime import datetime
from sqlglot import parse_one, transpile
from app.db.engine import get_session
from app.utils.logger import get_logger

logger = get_logger('migrate')

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
        "bk_property_index": -2,
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    },
    {
        "bk_property_id": "bk_inst_name",
        "bk_property_name": "实例名称",
        "bk_property_type": "singlechar",
        "isrequired": False,
        "isreadonly": True,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": False,
        "bk_isapi": False,
        "bk_issystem": True,
        "ispre": True,
        "bk_property_index": -3,
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    },
    {
        "bk_property_id": "_id",
        "bk_property_name": "记录ID",
        "bk_property_type": "singlechar",
        "isrequired": False,
        "isreadonly": True,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": True,
        "bk_isapi": False,
        "bk_issystem": True,
        "ispre": True,
        "bk_property_index": -4,
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    },
    {
        "bk_property_id": "bk_supplier_account",
        "bk_property_name": "供应商账户",
        "bk_property_type": "singlechar",
        "isrequired": False,
        "isreadonly": True,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": True,
        "bk_isapi": False,
        "bk_issystem": True,
        "ispre": True,
        "bk_property_index": -5,
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    },
    {
        "bk_property_id": "create_time",
        "bk_property_name": "创建时间",
        "bk_property_type": "time",
        "isrequired": False,
        "isreadonly": True,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": False,
        "bk_isapi": False,
        "bk_issystem": True,
        "ispre": True,
        "bk_property_index": -10,
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    },
    {
        "bk_property_id": "last_time",
        "bk_property_name": "更新时间",
        "bk_property_type": "time",
        "isrequired": False,
        "isreadonly": True,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": False,
        "bk_isapi": False,
        "bk_issystem": True,
        "ispre": True,
        "bk_property_index": -11,
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    }
]

# 分类数据
CLASSIFICATIONS = [
    {"id": 1, "bk_classification_id": "bk_network", "bk_classification_name": "网络", 
     "bk_classification_icon": "icon-cc-network", "ispre": True},
    {"id": 2, "bk_classification_id": "bk_host_manage", "bk_classification_name": "主机管理", 
     "bk_classification_icon": "icon-cc-host", "ispre": True},
    {"id": 3, "bk_classification_id": "bk_loadbalance", "bk_classification_name": "负载均衡", 
     "bk_classification_icon": "icon-cc-loadbalance", "ispre": True},
]

# 模型-分类映射
MODEL_CLASSIFICATION_MAP = {
    "bk_switch": "bk_network",
    "bk_host": "bk_host_manage",
    "bk_slb": "bk_loadbalance",
    "bk_slb_server": "bk_loadbalance",
    "bk_slb_listener": "bk_loadbalance",
}

class DatabaseMigrator:
    """数据库迁移工具"""
    
    def __init__(self, dialect='sqlite'):
        self.dialect = dialect
        self.session = get_session()
        self.project_root = Path(__file__).parent.parent.parent
    
    def translate_sql(self, sql, target_dialect=None):
        """使用 sqlglot 翻译 SQL"""
        target = target_dialect or self.dialect
        try:
            translated = transpile(sql, read='sqlite', write=target)
            return translated[0]
        except Exception as e:
            logger.warning(f"SQL 翻译失败: {e}")
            return sql
    
    def execute_sql(self, sql, params=None):
        """执行 SQL"""
        try:
            result = self.session.execute(sql, params or {})
            self.session.commit()
            return result
        except Exception as e:
            self.session.rollback()
            logger.error(f"SQL 执行失败: {e}")
            raise
    
    def execute_query(self, sql, params=None):
        """执行查询并返回结果"""
        result = self.execute_sql(sql, params)
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]
    
    def init_core_tables(self):
        """初始化核心表"""
        logger.info("初始化核心表...")
        
        # cc_ObjClassification - 分类表
        self.execute_sql("""
            CREATE TABLE IF NOT EXISTS cc_ObjClassification (
                id INTEGER PRIMARY KEY,
                bk_classification_id TEXT,
                bk_classification_name TEXT,
                bk_classification_icon TEXT,
                bk_classification_type TEXT,
                bk_ishidden INTEGER DEFAULT 0,
                bk_supplier_account TEXT DEFAULT '0',
                create_time TEXT,
                creator TEXT,
                ispre INTEGER DEFAULT 1,
                last_time TEXT,
                modifier TEXT
            )
        """)
        
        # cc_ObjDes - 模型表
        self.execute_sql("""
            CREATE TABLE IF NOT EXISTS cc_ObjDes (
                id INTEGER PRIMARY KEY,
                _id TEXT,
                bk_classification_id TEXT,
                bk_ishidden INTEGER DEFAULT 0,
                bk_ispaused INTEGER DEFAULT 0,
                bk_obj_icon TEXT,
                bk_obj_id TEXT,
                bk_obj_name TEXT,
                bk_supplier_account TEXT DEFAULT '0',
                create_time TEXT,
                creator TEXT,
                id INTEGER,
                ispre INTEGER DEFAULT 1,
                last_time TEXT,
                modifier TEXT,
                obj_sort_number INTEGER DEFAULT 0,
                position TEXT
            )
        """)
        
        # cc_ObjAttDes - 属性表
        self.execute_sql("""
            CREATE TABLE IF NOT EXISTS cc_ObjAttDes (
                id INTEGER PRIMARY KEY,
                _id TEXT,
                bk_isapi INTEGER DEFAULT 0,
                bk_ishidden INTEGER DEFAULT 0,
                bk_ispassword INTEGER DEFAULT 0,
                bk_issystem INTEGER DEFAULT 0,
                bk_obj_id TEXT,
                bk_property_group TEXT,
                bk_property_id TEXT,
                bk_property_index INTEGER DEFAULT 0,
                bk_property_name TEXT,
                bk_property_option TEXT,
                bk_property_type TEXT,
                bk_supplier_account TEXT DEFAULT '0',
                create_time TEXT,
                creator TEXT,
                default_columns TEXT,
                editable INTEGER DEFAULT 0,
                id INTEGER,
                ispre INTEGER DEFAULT 1,
                isreadonly INTEGER DEFAULT 0,
                isrequired INTEGER DEFAULT 0,
                last_time TEXT,
                modifier TEXT,
                option TEXT,
                placeholder TEXT,
                unit TEXT
            )
        """)
        
        # cc_ObjAsst - 对象关联表
        self.execute_sql("""
            CREATE TABLE IF NOT EXISTS cc_ObjAsst (
                id INTEGER PRIMARY KEY,
                _id TEXT,
                bk_asst_id TEXT,
                bk_obj_id TEXT,
                bk_supplier_account TEXT DEFAULT '0',
                cardinality TEXT,
                create_time TEXT,
                creator TEXT,
                dest_des TEXT,
                id INTEGER,
                ispre INTEGER DEFAULT 1,
                last_time TEXT,
                modifier TEXT,
                obj_asst_id TEXT,
                obj_asst_name TEXT,
                position TEXT,
                source_des TEXT,
                target_obj_id TEXT,
                target_obj_name TEXT
            )
        """)
        
        # cc_AsstDes - 关联类型表
        self.execute_sql("""
            CREATE TABLE IF NOT EXISTS cc_AsstDes (
                id INTEGER PRIMARY KEY,
                _id TEXT,
                bk_asst_id TEXT,
                bk_asst_name TEXT,
                bk_supplier_account TEXT DEFAULT '0',
                create_time TEXT,
                creator TEXT,
                dest_des TEXT,
                direction TEXT,
                id INTEGER,
                ispre INTEGER DEFAULT 1,
                last_time TEXT,
                modifier TEXT,
                position TEXT,
                source_des TEXT
            )
        """)
        
        # cc_InstAsst_0_pub - 实例关联表
        self.execute_sql("""
            CREATE TABLE IF NOT EXISTS cc_InstAsst_0_pub (
                id INTEGER PRIMARY KEY,
                _id TEXT,
                bk_asst_inst_id INTEGER,
                bk_asst_obj_id TEXT,
                bk_inst_id INTEGER,
                bk_obj_asst_id TEXT,
                bk_obj_id TEXT,
                bk_relation_type_id TEXT,
                bk_supplier_account TEXT DEFAULT '0',
                create_time TEXT,
                creator TEXT,
                id INTEGER,
                ispre INTEGER DEFAULT 1,
                last_time TEXT,
                modifier TEXT
            )
        """)
        
        # user_custom - 用户配置表
        self.execute_sql("""
            CREATE TABLE IF NOT EXISTS user_custom (
                id INTEGER PRIMARY KEY,
                user_name TEXT DEFAULT 'admin',
                config_key TEXT,
                config_value TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # users - 用户表
        self.execute_sql("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                user_name TEXT UNIQUE NOT NULL,
                display_name TEXT,
                created_at TEXT
            )
        """)
        
        logger.info("核心表初始化完成")
    
    def migrate_classifications(self):
        """迁移分类数据"""
        now = datetime.now().isoformat()
        
        for cls in CLASSIFICATIONS:
            self.execute_sql("""
                INSERT OR REPLACE INTO cc_ObjClassification
                (id, bk_classification_id, bk_classification_name, bk_classification_icon, 
                 ispre, bk_supplier_account, create_time, last_time, creator, modifier)
                VALUES (:id, :bk_classification_id, :bk_classification_name, :bk_classification_icon,
                        :ispre, '0', :now, :now, 'admin', 'admin')
            """, {
                **cls,
                'now': now
            })
        
        logger.info(f"迁移了 {len(CLASSIFICATIONS)} 个分类")
    
    def migrate_models(self):
        """迁移模型数据"""
        ui_project = self.project_root / "cmdb_ui_lite" / "src" / "assets" / "api"
        index_path = ui_project / "index.json"
        
        if not index_path.exists():
            logger.warning(f"找不到模型数据文件: {index_path}")
            return
        
        with open(index_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        now = datetime.now().isoformat()
        
        for idx, model in enumerate(data.get("models", [])):
            model_id = model.get("bk_obj_id")
            classification_id = MODEL_CLASSIFICATION_MAP.get(model_id, "bk_uncategorized")
            
            self.execute_sql("""
                INSERT OR REPLACE INTO cc_ObjDes 
                (_id, id, bk_obj_id, bk_obj_name, bk_obj_icon, bk_classification_id, ispre,
                 bk_supplier_account, create_time, last_time, creator, modifier, obj_sort_number)
                VALUES (:_id, :id, :bk_obj_id, :bk_obj_name, :bk_obj_icon, :bk_classification_id,
                        :ispre, '0', :now, :now, 'admin', 'admin', :obj_sort_number)
            """, {
                '_id': model_id,
                'id': idx + 1,
                'bk_obj_id': model_id,
                'bk_obj_name': model.get("bk_obj_name"),
                'bk_obj_icon': model.get("bk_obj_icon"),
                'bk_classification_id': classification_id,
                'ispre': True,
                'now': now,
                'obj_sort_number': idx
            })
        
        logger.info(f"迁移了 {len(data.get('models', []))} 个模型")
    
    def migrate_attributes(self):
        """迁移属性数据"""
        ui_project = self.project_root / "cmdb_ui_lite" / "src" / "assets" / "api"
        index_path = ui_project / "index.json"
        
        if not index_path.exists():
            logger.warning(f"找不到模型数据文件: {index_path}")
            return
        
        with open(index_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        now = datetime.now().isoformat()
        attr_id = 1
        
        for model in data.get("models", []):
            model_id = model.get("bk_obj_id")
            attr_file_path = ui_project / "attributes" / f"{model_id}.json"
            
            if not attr_file_path.exists():
                continue
            
            try:
                with open(attr_file_path, 'r', encoding='utf-8') as f:
                    attr_data = json.load(f)
                
                properties = attr_data.get("info", [])
                
                # 先插入系统属性
                for sys_prop in SYSTEM_PROPERTIES:
                    option = sys_prop.get("option")
                    option_json = json.dumps(option) if option else None
                    
                    self.execute_sql("""
                        INSERT OR REPLACE INTO cc_ObjAttDes
                        (_id, id, bk_obj_id, bk_property_id, bk_property_name, bk_property_type,
                         bk_property_index, bk_property_option, option, isrequired, isreadonly,
                         editable, bk_ispassword, bk_ishidden, bk_isapi, bk_issystem, ispre,
                         bk_property_group, placeholder, unit, bk_supplier_account, create_time,
                         last_time, creator, modifier)
                        VALUES (:_id, :id, :bk_obj_id, :bk_property_id, :bk_property_name,
                                :bk_property_type, :bk_property_index, :bk_property_option, :option,
                                :isrequired, :isreadonly, :editable, :bk_ispassword, :bk_ishidden,
                                :bk_isapi, :bk_issystem, :ispre, :bk_property_group, :placeholder,
                                :unit, '0', :now, :now, 'admin', 'admin')
                    """, {
                        '_id': f"{model_id}.{sys_prop['bk_property_id']}",
                        'id': attr_id,
                        'bk_obj_id': model_id,
                        'bk_property_id': sys_prop['bk_property_id'],
                        'bk_property_name': sys_prop['bk_property_name'],
                        'bk_property_type': sys_prop['bk_property_type'],
                        'bk_property_index': sys_prop['bk_property_index'],
                        'bk_property_option': option_json,
                        'option': option_json,
                        'isrequired': sys_prop['isrequired'],
                        'isreadonly': sys_prop['isreadonly'],
                        'editable': sys_prop['editable'],
                        'bk_ispassword': sys_prop['bk_ispassword'],
                        'bk_ishidden': sys_prop['bk_ishidden'],
                        'bk_isapi': sys_prop['bk_isapi'],
                        'bk_issystem': sys_prop['bk_issystem'],
                        'ispre': sys_prop['ispre'],
                        'bk_property_group': sys_prop['bk_property_group'],
                        'placeholder': sys_prop['placeholder'],
                        'unit': sys_prop['unit'],
                        'now': now
                    })
                    attr_id += 1
                
                # 插入业务属性
                for prop in properties:
                    if prop.get('bk_property_id') in SYSTEM_FIELDS:
                        continue
                    
                    option = prop.get("option") or prop.get("bk_property_option")
                    option_json = json.dumps(option) if option else None
                    
                    self.execute_sql("""
                        INSERT OR REPLACE INTO cc_ObjAttDes
                        (_id, id, bk_obj_id, bk_property_id, bk_property_name, bk_property_type,
                         bk_property_index, bk_property_option, option, isrequired, isreadonly,
                         editable, bk_ispassword, bk_ishidden, bk_isapi, bk_issystem, ispre,
                         bk_property_group, placeholder, unit, bk_supplier_account, create_time,
                         last_time, creator, modifier)
                        VALUES (:_id, :id, :bk_obj_id, :bk_property_id, :bk_property_name,
                                :bk_property_type, :bk_property_index, :bk_property_option, :option,
                                :isrequired, :isreadonly, :editable, :bk_ispassword, :bk_ishidden,
                                :bk_isapi, :bk_issystem, :ispre, :bk_property_group, :placeholder,
                                :unit, '0', :now, :now, 'admin', 'admin')
                    """, {
                        '_id': f"{model_id}.{prop['bk_property_id']}",
                        'id': attr_id,
                        'bk_obj_id': model_id,
                        'bk_property_id': prop['bk_property_id'],
                        'bk_property_name': prop['bk_property_name'],
                        'bk_property_type': prop['bk_property_type'],
                        'bk_property_index': prop.get('bk_property_index', attr_id),
                        'bk_property_option': option_json,
                        'option': option_json,
                        'isrequired': prop.get('isrequired', False),
                        'isreadonly': prop.get('isreadonly', False),
                        'editable': prop.get('editable', True),
                        'bk_ispassword': prop.get('bk_ispassword', False),
                        'bk_ishidden': prop.get('bk_ishidden', False),
                        'bk_isapi': prop.get('bk_isapi', False),
                        'bk_issystem': prop.get('bk_issystem', False),
                        'ispre': prop.get('ispre', True),
                        'bk_property_group': prop.get('bk_property_group', 'default'),
                        'placeholder': prop.get('placeholder', ''),
                        'unit': prop.get('unit', ''),
                        'now': now
                    })
                    attr_id += 1
                
                logger.info(f"为模型 {model_id} 迁移了 {len(properties) + len(SYSTEM_PROPERTIES)} 个属性")
                
            except Exception as e:
                logger.error(f"迁移模型 {model_id} 属性失败: {e}")
    
    def create_instance_table(self, model_id):
        """为模型创建实例表"""
        table_name = f"cc_ObjectBase_0_pub_{model_id}"
        
        # 先查询模型属性定义
        attributes = self.execute_query("""
            SELECT bk_property_id, bk_property_type, isrequired, option
            FROM cc_ObjAttDes 
            WHERE bk_obj_id = :model_id
            ORDER BY bk_property_index
        """, {'model_id': model_id})
        
        # 构建建表语句
        columns = []
        for attr in attributes:
            prop_id = attr['bk_property_id']
            prop_type = attr['bk_property_type']
            
            # 映射属性类型到 SQL 类型
            sql_type = self.get_sql_type(prop_type)
            
            columns.append(f'"{prop_id}" {sql_type}')
        
        if columns:
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS "{table_name}" ({', '.join(columns)})
            """
            self.execute_sql(create_sql)
            logger.info(f"创建实例表: {table_name}")
    
    def get_sql_type(self, prop_type):
        """获取属性类型对应的 SQL 类型"""
        type_mapping = {
            'int': 'INTEGER',
            'number': 'REAL',
            'singlechar': 'TEXT',
            'longchar': 'TEXT',
            'char': 'TEXT',
            'enum': 'TEXT',
            'enumMulti': 'TEXT',
            'bool': 'INTEGER',
            'time': 'TEXT',
            'date': 'TEXT',
            'datetime': 'TEXT',
            'list': 'TEXT',
            'objuser': 'TEXT',
            'orgid': 'TEXT',
            'timezone': 'TEXT'
        }
        return type_mapping.get(prop_type, 'TEXT')
    
    def migrate_relation_types(self):
        """迁移关联类型数据"""
        now = datetime.now().isoformat()
        
        # 插入示例关联类型
        relation_types = [
            {
                'bk_asst_id': 'bk_relation',
                'bk_asst_name': '关联关系',
                'direction': 'forward',
                'source_des': '源',
                'dest_des': '目标'
            }
        ]
        
        for idx, rel_type in enumerate(relation_types):
            self.execute_sql("""
                INSERT OR REPLACE INTO cc_AsstDes
                (_id, id, bk_asst_id, bk_asst_name, direction, source_des, dest_des,
                 bk_supplier_account, create_time, last_time, creator, modifier, ispre)
                VALUES (:_id, :id, :bk_asst_id, :bk_asst_name, :direction, :source_des, :dest_des,
                        '0', :now, :now, 'admin', 'admin', 1)
            """, {
                '_id': rel_type['bk_asst_id'],
                'id': idx + 1,
                'now': now,
                **rel_type
            })
        
        logger.info("迁移关联类型完成")
    
    def migrate_object_associations(self):
        """迁移对象关联"""
        now = datetime.now().isoformat()
        
        # 示例对象关联
        obj_associations = [
            {
                'bk_obj_id': 'bk_host',
                'target_obj_id': 'bk_slb',
                'target_obj_name': '负载均衡',
                'bk_asst_id': 'bk_relation',
                'cardinality': 'n:1',
                'source_des': '主机',
                'dest_des': '负载均衡'
            },
            {
                'bk_obj_id': 'bk_slb',
                'target_obj_id': 'bk_slb_listener',
                'target_obj_name': '负载均衡-监听',
                'bk_asst_id': 'bk_relation',
                'cardinality': '1:n',
                'source_des': '负载均衡',
                'dest_des': '监听'
            },
            {
                'bk_obj_id': 'bk_slb_listener',
                'target_obj_id': 'bk_slb_server',
                'target_obj_name': '负载均衡-服务器',
                'bk_asst_id': 'bk_relation',
                'cardinality': '1:n',
                'source_des': '监听',
                'dest_des': '服务器'
            }
        ]
        
        for idx, assoc in enumerate(obj_associations):
            obj_asst_id = f"{assoc['bk_obj_id']}_{assoc['target_obj_id']}"
            
            self.execute_sql("""
                INSERT OR REPLACE INTO cc_ObjAsst
                (_id, id, bk_obj_id, target_obj_id, target_obj_name, bk_asst_id, cardinality,
                 source_des, dest_des, obj_asst_id, obj_asst_name, bk_supplier_account,
                 create_time, last_time, creator, modifier, ispre)
                VALUES (:_id, :id, :bk_obj_id, :target_obj_id, :target_obj_name, :bk_asst_id,
                        :cardinality, :source_des, :dest_des, :obj_asst_id, :obj_asst_name,
                        '0', :now, :now, 'admin', 'admin', 1)
            """, {
                '_id': obj_asst_id,
                'id': idx + 1,
                'now': now,
                'obj_asst_id': obj_asst_id,
                'obj_asst_name': f"{assoc['source_des']}->{assoc['dest_des']}",
                **assoc
            })
        
        logger.info("迁移对象关联完成")
    
    def init_users(self):
        """初始化用户数据"""
        now = datetime.now().isoformat()
        
        self.execute_sql("""
            INSERT OR REPLACE INTO users (id, user_name, display_name, created_at)
            VALUES (1, 'admin', 'Administrator', :now)
        """, {'now': now})
        
        logger.info("初始化用户数据完成")
    
    def run_migration(self):
        """运行完整迁移"""
        logger.info("="*50)
        logger.info("开始数据库迁移")
        logger.info("="*50)
        
        try:
            # 初始化核心表
            self.init_core_tables()
            
            # 迁移分类
            self.migrate_classifications()
            
            # 迁移模型
            self.migrate_models()
            
            # 迁移属性
            self.migrate_attributes()
            
            # 迁移关联类型
            self.migrate_relation_types()
            
            # 迁移对象关联
            self.migrate_object_associations()
            
            # 初始化用户
            self.init_users()
            
            # 为每个模型创建实例表
            models = self.execute_query("SELECT DISTINCT bk_obj_id FROM cc_ObjDes")
            for model in models:
                model_id = model['bk_obj_id']
                self.create_instance_table(model_id)
            
            logger.info("="*50)
            logger.info("数据库迁移完成!")
            logger.info("="*50)
            
        except Exception as e:
            logger.error(f"迁移失败: {e}")
            raise
    
    def drop_all_tables(self):
        """删除所有表（用于开发时重置）"""
        logger.warning("删除所有表...")
        
        tables = self.execute_query("""
            SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        
        for table in tables:
            table_name = table['name']
            try:
                self.execute_sql(f"DROP TABLE IF EXISTS {table_name}")
                logger.info(f"删除表: {table_name}")
            except Exception as e:
                logger.error(f"删除表 {table_name} 失败: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库迁移工具')
    parser.add_argument('--dialect', default='sqlite', help='数据库方言 (sqlite/mysql/postgres)')
    parser.add_argument('--drop', action='store_true', help='删除所有表（重置）')
    parser.add_argument('--migration', action='store_true', help='运行迁移')
    
    args = parser.parse_args()
    
    migrator = DatabaseMigrator(dialect=args.dialect)
    
    if args.drop:
        migrator.drop_all_tables()
    
    if args.migration:
        migrator.run_migration()


if __name__ == "__main__":
    main()
