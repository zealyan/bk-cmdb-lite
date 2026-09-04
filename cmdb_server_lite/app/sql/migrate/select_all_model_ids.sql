-- 全部模型 ID（迁移期遍历模型的入口查询，5 处复用）
-- 方言：以 ANSI/PostgreSQL 通用子集书写，执行层 adapt_sql 转译为当前目标方言。
SELECT bk_obj_id
FROM cc_ObjDes
