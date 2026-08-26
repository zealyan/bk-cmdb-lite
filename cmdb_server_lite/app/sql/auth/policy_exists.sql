-- 精确存在性判定（用于 grant 幂等）：所有维度（含 obj_id / business_id）按「值相等或同为 NULL」严格匹配。
-- 与 select_policies.sql 的继承语义不同：这里不做「类级 NULL 覆盖」展开，确保
--   (business_id='2') 与 (business_id=NULL=全部业务) 被视为两条独立策略，互不跳过。
SELECT id
FROM cc_AuthPolicy
WHERE supplier = :supplier
  AND principal = :principal
  AND res_type = :res_type
  AND (obj_id = :obj_id OR (obj_id IS NULL AND :obj_id IS NULL))
  AND action = :action
  AND (business_id = :business_id OR (business_id IS NULL AND :business_id IS NULL))
