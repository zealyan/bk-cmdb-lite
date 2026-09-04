-- 按 (模型, 属性) 取属性自增 ID —— 判断属性是否已存在并复用其 id，
-- 避免重跑迁移时给同一属性分配新 id（6 处复用）。
-- (bk_obj_id, bk_property_id) 是 cc_ObjAttDes 的复合主键，最多返回 1 行。
SELECT id
FROM cc_ObjAttDes
WHERE bk_obj_id = :bk_obj_id
  AND bk_property_id = :bk_property_id
