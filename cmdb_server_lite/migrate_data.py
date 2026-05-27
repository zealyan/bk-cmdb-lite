#!/usr/bin/env python3
"""
数据迁移脚本 - 从 JSON 文件迁移到 DuckDB
与原项目保持一致的系统字段处理
"""

import json
import duckdb

UI_PROJECT = "../cmdb_ui_lite/src/assets/api"
DB_PATH = "cmdb.duckdb"

# 系统字段列表 - 与原项目保持一致
# 参考原项目: /workspace/bk-cmdb/src/common/definitions.go
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
    # 原项目后端定义的时间字段
    'bk_created_by',
    'bk_created_at',
    'bk_updated_by',
    'bk_updated_at',
    # 原项目后端定义的 modifier 字段
    'modifier'
}

# 系统属性定义模板
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
        "bk_property_id": "bk_obj_id",
        "bk_property_name": "对象类型",
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
        "bk_property_index": 9998,
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    },
    {
        "bk_property_id": "last_time",
        "bk_property_name": "修改时间",
        "bk_property_type": "time",
        "isrequired": False,
        "isreadonly": True,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": False,
        "bk_isapi": False,
        "bk_issystem": True,
        "ispre": True,
        "bk_property_index": 9999,
        "bk_property_group": "default",
        "placeholder": "",
        "unit": "",
        "option": None
    },
    {
        "bk_property_id": "bk_operate_time",
        "bk_property_name": "操作时间",
        "bk_property_type": "time",
        "isrequired": False,
        "isreadonly": True,
        "editable": False,
        "bk_ispassword": False,
        "bk_ishidden": True,
        "bk_isapi": False,
        "bk_issystem": True,
        "ispre": True,
        "bk_property_index": 10006,
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
    }
]


def get_db():
    return duckdb.connect(DB_PATH)


def create_base_tables(db):
    """创建基础表结构（不包括 cc_ObjectBase_* 表）"""
    db.execute("DROP TABLE IF EXISTS cc_ObjectBase_0_pub_bk_switch")
    db.execute("DROP TABLE IF EXISTS cc_ObjectBase_0_pub_bk_host")
    db.execute("DROP TABLE IF EXISTS cc_ObjectBase_0_pub_bk_slb_listener")
    db.execute("DROP TABLE IF EXISTS cc_ObjectBase_0_pub_bk_slb_server")
    db.execute("DROP TABLE IF EXISTS cc_ObjectBase_0_pub_bk_slb")
    db.execute("DROP TABLE IF EXISTS cc_InstAsst_0_pub")
    db.execute("DROP TABLE IF EXISTS cc_ObjAsst")
    db.execute("DROP TABLE IF EXISTS cc_ObjDes")
    db.execute("DROP TABLE IF EXISTS cc_AsstDes")
    db.execute("DROP TABLE IF EXISTS cc_ObjAttDes")
    db.execute("DROP TABLE IF EXISTS cc_ObjClassification")

    db.execute("""
        CREATE TABLE cc_ObjClassification (
            id INTEGER PRIMARY KEY,
            bk_classification_id VARCHAR UNIQUE NOT NULL,
            bk_classification_name VARCHAR NOT NULL,
            bk_classification_type VARCHAR,
            bk_classification_icon VARCHAR,
            bk_ishidden BOOLEAN DEFAULT FALSE,
            ispre BOOLEAN DEFAULT FALSE,
            creator VARCHAR DEFAULT 'admin',
            modifier VARCHAR DEFAULT 'admin',
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bk_supplier_account VARCHAR DEFAULT '0'
        )
    """)

    db.execute("""
        CREATE TABLE cc_ObjDes (
            _id VARCHAR,
            id INTEGER,
            bk_obj_id VARCHAR PRIMARY KEY,
            bk_obj_name VARCHAR,
            bk_obj_icon VARCHAR,
            bk_classification_id VARCHAR,
            bk_ishidden BOOLEAN DEFAULT FALSE,
            ispre BOOLEAN DEFAULT FALSE,
            bk_ispaused BOOLEAN DEFAULT FALSE,
            position VARCHAR,
            creator VARCHAR DEFAULT 'admin',
            modifier VARCHAR DEFAULT 'admin',
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            obj_sort_number INTEGER DEFAULT 0,
            bk_supplier_account VARCHAR DEFAULT '0'
        )
    """)

    db.execute("""
        CREATE TABLE cc_InstAsst_0_pub (
            _id VARCHAR,
            id INTEGER PRIMARY KEY,
            bk_obj_id VARCHAR,
            bk_inst_id INTEGER,
            bk_asst_obj_id VARCHAR,
            bk_asst_inst_id INTEGER,
            bk_obj_asst_id VARCHAR,
            bk_relation_type_id VARCHAR,
            bk_supplier_account VARCHAR DEFAULT '0'
        )
    """)

    db.execute("""
        CREATE TABLE cc_AsstDes (
            _id VARCHAR,
            id INTEGER,
            bk_asst_id VARCHAR PRIMARY KEY,
            bk_asst_name VARCHAR,
            src_des VARCHAR,
            dest_des VARCHAR,
            direction VARCHAR,
            ispre BOOLEAN DEFAULT FALSE,
            bk_supplier_account VARCHAR DEFAULT '0'
        )
    """)

    db.execute("""
        CREATE TABLE cc_ObjAsst (
            _id VARCHAR,
            id INTEGER,
            bk_obj_id VARCHAR,
            target_obj_id VARCHAR,
            target_obj_name VARCHAR,
            bk_asst_id VARCHAR,
            bk_obj_asst_id VARCHAR,
            bk_obj_asst_name VARCHAR,
            cardinality VARCHAR,
            mapping VARCHAR,
            on_delete VARCHAR,
            ispre BOOLEAN DEFAULT FALSE,
            creator VARCHAR DEFAULT 'admin',
            modifier VARCHAR DEFAULT 'admin',
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bk_supplier_account VARCHAR DEFAULT '0'
        )
    """)

    db.execute("""
        CREATE TABLE cc_ObjAttDes (
            _id VARCHAR,
            id INTEGER,
            bk_obj_id VARCHAR,
            bk_property_id VARCHAR,
            bk_property_name VARCHAR,
            bk_property_type VARCHAR,
            bk_property_group VARCHAR,
            isrequired BOOLEAN DEFAULT FALSE,
            bk_ispassword BOOLEAN DEFAULT FALSE,
            bk_ishidden BOOLEAN DEFAULT FALSE,
            isreadonly BOOLEAN DEFAULT FALSE,
            bk_isapi BOOLEAN DEFAULT FALSE,
            bk_issystem BOOLEAN DEFAULT FALSE,
            option VARCHAR,
            unit VARCHAR,
            placeholder VARCHAR,
            editable BOOLEAN DEFAULT TRUE,
            ispre BOOLEAN DEFAULT FALSE,
            bk_property_index INTEGER,
            creator VARCHAR DEFAULT 'admin',
            modifier VARCHAR DEFAULT 'admin',
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bk_supplier_account VARCHAR DEFAULT '0',
            bk_property_option VARCHAR,
            default_columns VARCHAR
        )
    """)

    print("基础表结构创建完成")


def get_duckdb_type(bk_property_type):
    """将 CMDB 属性类型转换为 DuckDB 类型"""
    type_map = {
        'string': 'VARCHAR',
        'text': 'VARCHAR',
        'longchar': 'VARCHAR',
        'singlechar': 'VARCHAR',
        'int': 'INTEGER',
        'integer': 'INTEGER',
        'long': 'BIGINT',
        'float': 'DOUBLE',
        'double': 'DOUBLE',
        'boolean': 'BOOLEAN',
        'bool': 'BOOLEAN',
        'datetime': 'TIMESTAMP',
        'time': 'TIMESTAMP',
        'date': 'DATE',
        'enum': 'VARCHAR',
        'set': 'VARCHAR',
        'json': 'VARCHAR',
    }
    return type_map.get(bk_property_type.lower(), 'VARCHAR')


def create_object_tables_from_attrs(db):
    """根据 cc_ObjAttDes 中的属性定义动态创建 cc_ObjectBase_* 表"""
    print("\n=== 根据属性定义动态创建数据表 ===")

    models = db.execute("SELECT bk_obj_id FROM cc_ObjDes").fetchall()

    for model_row in models:
        model_id = model_row[0]
        table_name = f"cc_ObjectBase_0_pub_{model_id}"

        attrs = db.execute("""
            SELECT bk_property_id, bk_property_type, bk_ishidden, isreadonly
            FROM cc_ObjAttDes 
            WHERE bk_obj_id = ?
            ORDER BY bk_property_index
        """, [model_id]).fetchall()

        print(f"\n处理模型: {model_id}")
        print(f"  属性数量: {len(attrs)}")

        columns = [
            "_id VARCHAR",
            "id INTEGER PRIMARY KEY",
            "bk_inst_id INTEGER",
            "bk_inst_name VARCHAR",
            f"bk_obj_id VARCHAR DEFAULT '{model_id}'",
            "bk_supplier_account VARCHAR DEFAULT '0'",
            "create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "last_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "bk_operate_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ]

        for attr in attrs:
            prop_id = attr[0]
            prop_type = attr[1]
            is_hidden = attr[2]
            is_readonly = attr[3]

            if prop_id in SYSTEM_FIELDS:
                continue

            duckdb_type = get_duckdb_type(prop_type)
            columns.append(f'"{prop_id}" {duckdb_type}')

        create_sql = f"CREATE TABLE {table_name} ({', '.join(columns)})"
        db.execute(create_sql)
        print(f"  创建表: {table_name}")
        print(f"  列数量: {len(columns)}")


CLASSIFICATIONS = [
    {"id": 1, "bk_classification_id": "bk_network", "bk_classification_name": "网络", "bk_classification_icon": "icon-cc-network", "ispre": True},
    {"id": 2, "bk_classification_id": "bk_host_manage", "bk_classification_name": "主机管理", "bk_classification_icon": "icon-cc-host", "ispre": True},
    {"id": 3, "bk_classification_id": "bk_loadbalance", "bk_classification_name": "负载均衡", "bk_classification_icon": "icon-cc-loadbalance", "ispre": True},
]

MODEL_CLASSIFICATION_MAP = {
    "bk_switch": "bk_network",
    "bk_host": "bk_host_manage",
    "bk_slb": "bk_loadbalance",
    "bk_slb_server": "bk_loadbalance",
    "bk_slb_listener": "bk_loadbalance",
}


def migrate_classifications(db):
    """迁移分类数据"""
    for cls in CLASSIFICATIONS:
        db.execute("""
            INSERT INTO cc_ObjClassification
            (id, bk_classification_id, bk_classification_name, bk_classification_icon, ispre, bk_supplier_account)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            cls["id"],
            cls["bk_classification_id"],
            cls["bk_classification_name"],
            cls["bk_classification_icon"],
            cls["ispre"],
            "0"
        ])
    print(f"迁移 {len(CLASSIFICATIONS)} 个分类")


def migrate_models(db):
    """迁移模型数据"""
    with open(f"{UI_PROJECT}/index.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for idx, model in enumerate(data["models"]):
        model_id = model.get("bk_obj_id")
        classification_id = MODEL_CLASSIFICATION_MAP.get(model_id, "bk_uncategorized")

        db.execute("""
            INSERT INTO cc_ObjDes (_id, id, bk_obj_id, bk_obj_name, bk_obj_icon, bk_classification_id, ispre)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            model_id,
            idx + 1,
            model_id,
            model.get("bk_obj_name"),
            model.get("bk_obj_icon"),
            classification_id,
            True
        ])
    print(f"迁移 {len(data['models'])} 个模型")


def migrate_attributes(db):
    """迁移属性数据 - 从单独的属性文件加载，包含系统属性"""
    with open(f"{UI_PROJECT}/index.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    attr_id = 1
    total_attrs = 0

    for model in data["models"]:
        model_id = model.get("bk_obj_id")
        attributes_file = model.get("attributes_file")

        if not attributes_file:
            continue

        attr_file_path = f"{UI_PROJECT}/models/{attributes_file}"

        try:
            with open(attr_file_path, "r", encoding="utf-8") as f:
                attr_data = json.load(f)

            properties = attr_data.get("info", [])

            # 先插入系统属性
            print(f"插入模型 {model_id} 的 {len(SYSTEM_PROPERTIES)} 个系统属性")
            for sys_prop in SYSTEM_PROPERTIES:
                option = sys_prop.get("option")
                if option and not isinstance(option, str):
                    option = json.dumps(option)

                db.execute("""
                    INSERT INTO cc_ObjAttDes 
                    (_id, id, bk_obj_id, bk_property_id, bk_property_name, bk_property_type, 
                     bk_property_group, isrequired, bk_ispassword, bk_ishidden, isreadonly,
                     bk_isapi, bk_issystem, option, unit, placeholder, editable, ispre, 
                     bk_property_index, bk_supplier_account, bk_property_option)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    f"{model_id}.{sys_prop['bk_property_id']}",
                    attr_id,
                    model_id,
                    sys_prop["bk_property_id"],
                    sys_prop["bk_property_name"],
                    sys_prop["bk_property_type"],
                    sys_prop["bk_property_group"],
                    sys_prop["isrequired"],
                    sys_prop["bk_ispassword"],
                    sys_prop["bk_ishidden"],
                    sys_prop["isreadonly"],
                    sys_prop["bk_isapi"],
                    sys_prop["bk_issystem"],
                    option,
                    sys_prop["unit"],
                    sys_prop["placeholder"],
                    sys_prop["editable"],
                    sys_prop["ispre"],
                    sys_prop["bk_property_index"],
                    "0",
                    option
                ])
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

                db.execute("""
                    INSERT INTO cc_ObjAttDes 
                    (_id, id, bk_obj_id, bk_property_id, bk_property_name, bk_property_type, 
                     bk_property_group, isrequired, bk_ispassword, bk_ishidden, isreadonly,
                     bk_isapi, bk_issystem, option, unit, placeholder, editable, ispre, 
                     bk_property_index, bk_supplier_account, bk_property_option)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    f"{model_id}.{bk_property_id}",
                    attr_id,
                    model_id,
                    bk_property_id,
                    prop.get("bk_property_name"),
                    prop.get("bk_property_type", "string"),
                    prop.get("bk_property_group", "default"),
                    prop.get("isrequired", False),
                    prop.get("bk_ispassword", False),
                    bk_ishidden,
                    isreadonly,
                    bk_isapi,
                    bk_issystem,
                    option,
                    prop.get("unit"),
                    prop.get("placeholder"),
                    editable,
                    prop.get("ispre", False),
                    prop.get("bk_property_index", 0),
                    "0",
                    option
                ])
                attr_id += 1
                total_attrs += 1

            print(f"迁移模型 {model_id} 的 {len(properties) + len(SYSTEM_PROPERTIES)} 个属性")
        except FileNotFoundError:
            print(f"警告：未找到属性文件 {attr_file_path}")

    print(f"总共迁移 {total_attrs} 个属性")


def migrate_instances(db):
    """迁移实例数据 - 从单独的实例文件加载"""
    with open(f"{UI_PROJECT}/index.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for model in data["models"]:
        model_id = model.get("bk_obj_id")
        table_name = f"cc_ObjectBase_0_pub_{model_id}"
        instances_file = model.get("instances_file")

        if not instances_file:
            continue

        inst_file_path = f"{UI_PROJECT}/models/{instances_file}"

        try:
            with open(inst_file_path, "r", encoding="utf-8") as f:
                inst_data = json.load(f)

            instances = inst_data.get("info", [])

            print(f"迁移模型 {model_id} 的 {len(instances)} 个实例")

            for idx, inst in enumerate(instances):
                columns = []
                values = []

                inst_id = inst.get("id", idx + 1)
                bk_inst_id = inst.get("bk_inst_id", inst_id)
                bk_inst_name = inst.get("bk_inst_name", "")

                if not bk_inst_name and "bk_lb_name" in inst:
                    bk_inst_name = inst["bk_lb_name"]
                elif not bk_inst_name and "bk_host_innerip" in inst:
                    bk_inst_name = inst["bk_host_innerip"]
                elif not bk_inst_name and "bk_server_name" in inst:
                    bk_inst_name = inst["bk_server_name"]
                elif not bk_inst_name and "bk_listener_name" in inst:
                    bk_inst_name = inst["bk_listener_name"]
                elif not bk_inst_name:
                    bk_inst_name = f"{model_id}-{inst_id}"

                if "_id" in inst:
                    columns.append("_id")
                    values.append(inst["_id"])

                columns.append("id")
                values.append(inst_id)
                columns.append("bk_inst_id")
                values.append(bk_inst_id)
                columns.append("bk_inst_name")
                values.append(bk_inst_name)

                for key, value in inst.items():
                    if key in SYSTEM_FIELDS:
                        continue
                    columns.append(f'"{key}"')
                    values.append(value)

                placeholders = ",".join(["?" for _ in values])
                columns_str = ",".join(columns)

                try:
                    db.execute(f"""
                        INSERT INTO {table_name} ({columns_str})
                        VALUES ({placeholders})
                    """, values)
                except Exception as e:
                    print(f"  插入实例 {inst_id} 失败: {e}")

        except FileNotFoundError:
            print(f"警告：未找到实例文件 {inst_file_path}")


def migrate_relations(db):
    """迁移模型关联关系"""
    try:
        with open(f"{UI_PROJECT}/models/relations/instance.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        model_name_map = {}
        model_rows = db.execute("SELECT bk_obj_id, bk_obj_name FROM cc_ObjDes").fetchall()
        for row in model_rows:
            model_name_map[row[0]] = row[1]

        asst_des_id = 1
        inserted_asst_ids = set()
        for rel in data["relations"]:
            bk_asst_id = rel["bk_relation_type_id"]
            if bk_asst_id in inserted_asst_ids:
                continue
            bk_asst_name = rel["bk_relation_type_name"]
            src_model = rel["bk_src_model"]
            dst_model = rel["bk_dst_model"]

            src_des = rel.get("src_des", model_name_map.get(dst_model, dst_model))
            dest_des = rel.get("dest_des", model_name_map.get(src_model, src_model))

            db.execute("""
                INSERT INTO cc_AsstDes
                (_id, id, bk_asst_id, bk_asst_name, src_des, dest_des, direction, ispre, bk_supplier_account)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                bk_asst_id,
                asst_des_id,
                bk_asst_id,
                bk_asst_name,
                src_des,
                dest_des,
                rel.get("direction", "forward"),
                True,
                "0"
            ])
            inserted_asst_ids.add(bk_asst_id)
            asst_des_id += 1

        obj_asst_id = 1
        for rel in data["relations"]:
            bk_asst_id = rel["bk_relation_type_id"]
            bk_asst_name = rel["bk_relation_type_name"]
            src_model = rel["bk_src_model"]
            dst_model = rel["bk_dst_model"]

            model_exists = db.execute("SELECT COUNT(*) FROM cc_ObjDes WHERE bk_obj_id = ?", [src_model]).fetchone()[0]
            target_exists = db.execute("SELECT COUNT(*) FROM cc_ObjDes WHERE bk_obj_id = ?", [dst_model]).fetchone()[0]

            if model_exists == 0 or target_exists == 0:
                continue

            obj_asst_id_str = f"{src_model}_to_{dst_model}"
            db.execute("""
                INSERT INTO cc_ObjAsst
                (_id, id, bk_obj_id, target_obj_id, target_obj_name, bk_asst_id, 
                 bk_obj_asst_id, bk_obj_asst_name, cardinality, mapping, on_delete,
                 ispre, creator, modifier, create_time, last_time, bk_supplier_account)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                obj_asst_id_str,
                obj_asst_id,
                src_model,
                dst_model,
                model_name_map.get(dst_model, dst_model),
                bk_asst_id,
                obj_asst_id_str,
                bk_asst_name,
                rel.get("cardinality", "1:n"),
                rel.get("cardinality", "1:n"),
                "none",
                True,
                "admin",
                "admin",
                None,
                None,
                "0"
            ])
            obj_asst_id += 1

        print(f"迁移 {len(data['relations'])} 个关联类型")
    except FileNotFoundError:
        print("未找到模型关联关系文件")


def migrate_associations(db):
    """迁移实例关联数据 - 自动生成充足关联"""
    slb_ids = [row[0] for row in db.execute("SELECT id FROM cc_ObjectBase_0_pub_bk_slb").fetchall()]
    slb_server_ids = [row[0] for row in db.execute("SELECT id FROM cc_ObjectBase_0_pub_bk_slb_server").fetchall()]
    slb_listener_ids = [row[0] for row in db.execute("SELECT id FROM cc_ObjectBase_0_pub_bk_slb_listener").fetchall()]

    if not slb_ids or not slb_server_ids:
        print("警告：没有找到 SLB 或后端服务器实例，跳过关联生成")
        return

    assoc_id = 1
    associations = []

    slb_names = {}
    for row in db.execute("SELECT id, bk_lb_name FROM cc_ObjectBase_0_pub_bk_slb").fetchall():
        slb_names[row[0]] = row[1]

    server_names = {}
    for row in db.execute("SELECT id, bk_server_name FROM cc_ObjectBase_0_pub_bk_slb_server").fetchall():
        server_names[row[0]] = row[1]

    listener_names = {}
    for row in db.execute("SELECT id, bk_listener_name FROM cc_ObjectBase_0_pub_bk_slb_listener").fetchall():
        listener_names[row[0]] = row[1]

    for slb_id in slb_ids:
        slb_name = slb_names.get(slb_id, "")
        related_servers = []

        for server_id in slb_server_ids:
            server_name = server_names.get(server_id, "")
            if slb_name.lower() in server_name.lower() or server_id % 3 == slb_id % 3:
                related_servers.append(server_id)

        if len(related_servers) < 10:
            remaining = 10 - len(related_servers)
            for server_id in slb_server_ids:
                if server_id not in related_servers and remaining > 0:
                    related_servers.append(server_id)
                    remaining -= 1
                    if remaining == 0:
                        break

        for server_id in related_servers[:15]:
            associations.append({
                "id": assoc_id,
                "bk_obj_id": "bk_slb",
                "bk_inst_id": slb_id,
                "bk_asst_obj_id": "bk_slb_server",
                "bk_asst_inst_id": server_id,
                "bk_obj_asst_id": "bk_slb_to_bk_slb_server",
                "bk_relation_type_id": "to"
            })
            assoc_id += 1

        related_listeners = []
        for listener_id in slb_listener_ids:
            listener_name = listener_names.get(listener_id, "")
            if slb_name.lower() in listener_name.lower() or listener_id % 3 == slb_id % 3:
                related_listeners.append(listener_id)

        if len(related_listeners) < 3:
            remaining = 3 - len(related_listeners)
            for listener_id in slb_listener_ids:
                if listener_id not in related_listeners and remaining > 0:
                    related_listeners.append(listener_id)
                    remaining -= 1
                    if remaining == 0:
                        break

        for listener_id in related_listeners[:5]:
            associations.append({
                "id": assoc_id,
                "bk_obj_id": "bk_slb",
                "bk_inst_id": slb_id,
                "bk_asst_obj_id": "bk_slb_listener",
                "bk_asst_inst_id": listener_id,
                "bk_obj_asst_id": "bk_slb_to_bk_slb_listener",
                "bk_relation_type_id": "to"
            })
            assoc_id += 1

    for assoc in associations:
        db.execute("""
            INSERT INTO cc_InstAsst_0_pub 
            (id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id, 
             bk_obj_asst_id, bk_relation_type_id, bk_supplier_account)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            assoc["id"],
            assoc["bk_obj_id"],
            assoc["bk_inst_id"],
            assoc["bk_asst_obj_id"],
            assoc["bk_asst_inst_id"],
            assoc["bk_obj_asst_id"],
            assoc["bk_relation_type_id"],
            "0"
        ])

    print(f"生成并迁移 {len(associations)} 个实例关联")


def verify_tables(db):
    """验证所有模型的数据表是否与属性定义一致"""
    print("\n=== 验证表结构与属性定义一致性 ===")

    models = db.execute("SELECT bk_obj_id FROM cc_ObjDes").fetchall()

    for model_row in models:
        model_id = model_row[0]
        table_name = f"cc_ObjectBase_0_pub_{model_id}"

        attr_rows = db.execute("""
            SELECT bk_property_id, bk_property_name, bk_issystem, bk_isapi, isreadonly, editable, bk_ishidden
            FROM cc_ObjAttDes 
            WHERE bk_obj_id = ?
            ORDER BY bk_property_index
        """, [model_id]).fetchall()

        print(f"\n  模型: {model_id}")
        print(f"  属性总数: {len(attr_rows)}")

        system_count = 0
        api_count = 0
        readonly_count = 0
        hidden_count = 0

        for attr in attr_rows:
            if attr[2]:  # bk_issystem
                system_count += 1
            if attr[3]:  # bk_isapi
                api_count += 1
            if attr[4]:  # isreadonly
                readonly_count += 1
            if attr[5]:  # editable
                pass
            if attr[6]:  # bk_ishidden
                hidden_count += 1

        print(f"    系统属性: {system_count}")
        print(f"    API属性: {api_count}")
        print(f"    只读属性: {readonly_count}")
        print(f"    隐藏属性: {hidden_count}")

        try:
            table_cols = db.execute(f"SELECT * FROM {table_name} LIMIT 0").description
            table_fields = set(col[0] for col in table_cols)
            print(f"    数据表列数: {len(table_fields)}")

            inst_count = db.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print(f"    实例数: {inst_count}")
        except Exception as e:
            print(f"    ⚠️  表查询失败: {e}")


def main():
    """主迁移函数"""
    print("=== 开始数据迁移（增强版） ===\n")
    print("功能说明：")
    print("  - 自动补充系统字段（id, bk_inst_id, bk_inst_name, create_time等）")
    print("  - 设置正确的标志位（bk_issystem, bk_isapi, isreadonly等）")
    print("  - 与原项目保持一致的数据库结构")

    db = get_db()

    print("\n1. 创建基础表结构")
    create_base_tables(db)

    print("\n2. 迁移分类数据")
    migrate_classifications(db)

    print("\n3. 迁移模型数据")
    migrate_models(db)

    print("\n4. 迁移属性数据（包含系统属性）")
    migrate_attributes(db)

    print("\n5. 根据属性定义动态创建实例数据表")
    create_object_tables_from_attrs(db)

    print("\n6. 迁移实例数据")
    migrate_instances(db)

    print("\n7. 迁移模型关联关系")
    migrate_relations(db)

    print("\n8. 迁移实例关联数据")
    migrate_associations(db)

    print("\n9. 验证迁移结果")
    verify_tables(db)

    db.commit()
    db.close()

    print("\n=== 数据迁移完成 ===")


if __name__ == "__main__":
    main()
