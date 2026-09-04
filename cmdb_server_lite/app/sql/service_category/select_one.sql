-- 按 id + 租户查询单条服务分类
SELECT id, bk_biz_id, name, bk_root_id, bk_parent_id, bk_supplier_account, is_built_in
FROM cc_ServiceCategory
WHERE id = :cat_id
  AND bk_supplier_account = :bk_supplier_account
