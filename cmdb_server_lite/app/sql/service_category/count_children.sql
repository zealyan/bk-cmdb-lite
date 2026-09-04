-- 统计某分类下的直接子分类数量（有子分类则禁止删除，对齐上游与前端提示）
SELECT COUNT(*) AS cnt
FROM cc_ServiceCategory
WHERE bk_parent_id = :parent_id
  AND bk_supplier_account = :bk_supplier_account
