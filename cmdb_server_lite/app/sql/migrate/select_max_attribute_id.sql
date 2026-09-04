-- 当前最大属性 ID —— 新增属性时从此值 +1 递增分配（2 处复用）。
-- 空表时 MAX 返回 NULL，调用方需兜底为 0。
SELECT MAX(id) AS max_id
FROM cc_ObjAttDes
