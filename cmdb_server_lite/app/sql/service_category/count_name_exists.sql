-- 同级（bk_parent_id）下分类名称唯一校验（不区分大小写）
-- exclude_id 用于更新时排除自身
SELECT COUNT(*) AS cnt
FROM cc_ServiceCategory
WHERE bk_biz_id = :bk_biz_id
  AND bk_parent_id = :bk_parent_id
  AND bk_supplier_account = :bk_supplier_account
  AND LOWER(name) = LOWER(:name)
  AND id <> :exclude_id
