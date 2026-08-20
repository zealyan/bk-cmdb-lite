#!/usr/bin/env python3
import duckdb

DB_PATH = "cmdb.duckdb"


def verify_associations():
    print("=" * 60)
    print("验证 SLB 实例关联数据")
    print("=" * 60)

    db = duckdb.connect(DB_PATH)
    try:
        # 检查每个 SLB 实例的关联数量
        for slb_id in range(1, 11):
            count = db.execute(
                """
                SELECT COUNT(*) 
                FROM cc_InstAsst_0_pub 
                WHERE bk_obj_id = 'bk_slb' AND bk_inst_id = ?
                """,
                [slb_id]
            ).fetchone()[0]

            print(f"SLB ID {slb_id}: {count} 条关联数据")
            if count < 10:
                print(f"  ❌ 不满足要求！需要至少 10 条")
            else:
                print(f"  ✅ 满足要求")

        print("\n" + "=" * 60)
        print("验证详情")
        print("=" * 60)
        # 查询完整的关联信息
        result = db.execute(
            """
            SELECT bk_inst_id, bk_asst_obj_id, COUNT(*) as cnt 
            FROM cc_InstAsst_0_pub 
            WHERE bk_obj_id = 'bk_slb' 
            GROUP BY bk_inst_id, bk_asst_obj_id 
            ORDER BY bk_inst_id, bk_asst_obj_id
            """
        ).fetchall()

        print("\n按 SLB ID 和关联对象分类的统计：")
        for row in result:
            print(f"  SLB {row[0]} 关联 {row[1]}: {row[2]} 条")

    finally:
        db.close()


if __name__ == "__main__":
    verify_associations()
