-- 按自增 id + 租户查询单个关联类型
-- 对应上游 /api/v3/update|delete/associationtype/{id} 的按 id 定位语义
SELECT id,
       bk_asst_id,
       bk_asst_name,
       bk_asst_icon,
       src_des,
       dest_des,
       direction,
       ispre,
       creator,
       modifier,
       create_time,
       last_time,
       bk_supplier_account
FROM cc_AsstDes
WHERE id = :id
  AND bk_supplier_account = :bk_supplier_account
