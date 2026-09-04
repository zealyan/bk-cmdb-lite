-- 查询某业务 + 租户下可用的全部服务分类（扁平）
-- 对齐上游 coreservice ListServiceCategories
-- （src/source_controller/coreservice/core/process/service_category.go:216）：
--   filter: bk_biz_id IN [bizID, 0]
-- 即「本业务自有分类」+「bk_biz_id=0 的全局内置分类（内置 Default 两级）」一并返回。
-- 这正是「新建模块下拉能看到 Default，而服务分类列表页由前端自行过滤隐藏」的根因。
--
-- 排序：全局内置（bk_biz_id=0）优先，其次 name 升序（对齐上游 sort = "name"），
--       id 升序兜底保证顺序稳定（同名场景）。
-- 注意：bk_biz_id / name 均为 NOT NULL 且有默认值，故无需 NULLS LAST（PostgreSQL 专有语法，
--       在旧版 SQLite < 3.30 会报语法错误）；用纯 ASC 即可三方言一致输出。
-- 多方言：PostgreSQL 规范方言，运行时经 app.db.dialect 转译（sqlite / mysql 自动适配）
SELECT id, bk_biz_id, name, bk_root_id, bk_parent_id, bk_supplier_account, is_built_in
FROM cc_ServiceCategory
WHERE bk_biz_id IN (:bk_biz_id, 0)
  AND bk_supplier_account = :bk_supplier_account
ORDER BY bk_biz_id ASC, name ASC, id ASC
