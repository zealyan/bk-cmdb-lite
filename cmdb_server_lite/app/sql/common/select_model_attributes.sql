-- 获取模型属性
-- 参数: :bk_obj_id 模型ID

SELECT * FROM cc_ObjAttDes
WHERE bk_obj_id = :bk_obj_id
ORDER BY bk_property_index
