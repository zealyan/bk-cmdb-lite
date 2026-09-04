-- 统计某业务下各服务分类被模块（cc_ModuleBase.service_category_id）引用的数量。
-- 对应原项目 usage_amount 字段，供前端「分类被模块占用则禁用删除」逻辑使用。
-- 排除未分类模块（service_category_id 为 NULL / 0），仅统计真实引用。
SELECT service_category_id, COUNT(*) AS cnt
FROM cc_ModuleBase
WHERE bk_biz_id = :bk_biz_id
  AND bk_supplier_account = :bk_supplier_account
  AND service_category_id IS NOT NULL
  AND service_category_id <> 0
GROUP BY service_category_id
