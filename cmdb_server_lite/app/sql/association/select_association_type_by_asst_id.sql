-- 按 bk_asst_id + 租户查询单个关联类型
-- 用于创建时的唯一性判重（对齐上游 associationKind.isExists）
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
WHERE bk_asst_id = :bk_asst_id
  AND bk_supplier_account = :bk_supplier_account
