#!/usr/bin/env python3
"""只迁移关联关系数据的脚本"""

import sys
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from app.db.engine import get_connection
from sqlalchemy import text


def migrate_associations():
    """只迁移关联关系数据"""
    print("开始迁移关联关系数据...")

    # 1. 添加关联类型到 cc_AsstDes
    asst_types = [
        {
            "bk_asst_id": "slb_to_server",
            "bk_asst_name": "指向",
            "bk_supplier_account": "0",
            "ispre": True
        },
        {
            "bk_asst_id": "slb_to_listener",
            "bk_asst_name": "指向",
            "bk_supplier_account": "0",
            "ispre": True
        }
    ]

    conn = get_connection()
    try:
        for idx, asst_type in enumerate(asst_types, 1):
            conn.execute(text("""
                INSERT OR REPLACE INTO cc_AsstDes 
                (id, bk_asst_id, bk_asst_name, ispre, bk_supplier_account)
                VALUES (:id, :bk_asst_id, :bk_asst_name, :ispre, :bk_supplier_account)
            """), {
                "id": idx,
                "bk_asst_id": asst_type["bk_asst_id"],
                "bk_asst_name": asst_type["bk_asst_name"],
                "ispre": asst_type["ispre"],
                "bk_supplier_account": asst_type["bk_supplier_account"]
            })
        
        print(f"迁移了 {len(asst_types)} 个关联类型")

        # 2. 添加对象关联到 cc_ObjAsst
        obj_associations = [
            {
                "bk_obj_id": "bk_slb",
                "target_obj_id": "bk_slb_server",
                "target_obj_name": "后端服务器",
                "bk_asst_id": "slb_to_server",
                "bk_obj_asst_id": "bk_slb_to_bk_slb_server",
                "bk_obj_asst_name": "指向后端服务器",
                "bk_supplier_account": "0",
                "mapping": None,
                "on_delete": None
            },
            {
                "bk_obj_id": "bk_slb",
                "target_obj_id": "bk_slb_listener",
                "target_obj_name": "监听器",
                "bk_asst_id": "slb_to_listener",
                "bk_obj_asst_id": "bk_slb_to_bk_slb_listener",
                "bk_obj_asst_name": "指向监听器",
                "bk_supplier_account": "0",
                "mapping": None,
                "on_delete": None
            }
        ]

        for idx, obj_asst in enumerate(obj_associations, 1):
            conn.execute(text("""
                INSERT OR REPLACE INTO cc_ObjAsst 
                (id, bk_obj_id, target_obj_id, target_obj_name, bk_asst_id, 
                 bk_obj_asst_id, bk_obj_asst_name, mapping, on_delete, 
                 bk_supplier_account)
                VALUES (:id, :bk_obj_id, :target_obj_id, :target_obj_name, :bk_asst_id, 
                        :bk_obj_asst_id, :bk_obj_asst_name, :mapping, :on_delete, 
                        :bk_supplier_account)
            """), {
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
        
        print(f"迁移了 {len(obj_associations)} 个对象关联")

        # 3. 迁移实例关联数据
        ui_project = project_root.parent / "cmdb_ui_lite" / "src" / "assets" / "api"
        inst_assoc_file = ui_project / "models" / "associations" / "index.json"
        if inst_assoc_file.exists():
            with open(inst_assoc_file, 'r', encoding='utf-8') as f:
                inst_assoc_data = json.load(f)
            
            associations = inst_assoc_data.get("associations", [])
            
            for assoc in associations:
                # 确定 bk_obj_asst_id
                bk_obj_id = assoc.get("bk_obj_id")
                bk_asst_obj_id = assoc.get("bk_asst_obj_id")
                bk_obj_asst_id = f"{bk_obj_id}_to_{bk_asst_obj_id}"
                
                conn.execute(text("""
                    INSERT OR REPLACE INTO cc_InstAsst_0_pub 
                    (id, bk_obj_id, bk_inst_id, bk_asst_obj_id, bk_asst_inst_id, 
                     bk_obj_asst_id, bk_relation_type_id, bk_supplier_account)
                    VALUES (:id, :bk_obj_id, :bk_inst_id, :bk_asst_obj_id, :bk_asst_inst_id, 
                            :bk_obj_asst_id, :bk_relation_type_id, '0')
                """), {
                    "id": assoc.get("id"),
                    "bk_obj_id": bk_obj_id,
                    "bk_inst_id": assoc.get("bk_inst_id"),
                    "bk_asst_obj_id": bk_asst_obj_id,
                    "bk_asst_inst_id": assoc.get("bk_asst_inst_id"),
                    "bk_obj_asst_id": bk_obj_asst_id,
                    "bk_relation_type_id": assoc.get("bk_relation_type_id")
                })
            
            print(f"迁移了 {len(associations)} 个实例关联")
        else:
            print("警告: 未找到实例关联数据文件")

        conn.commit()
    finally:
        conn.close()

    print("关联关系数据迁移完成!")


if __name__ == "__main__":
    migrate_associations()
