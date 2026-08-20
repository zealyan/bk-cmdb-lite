-- 获取模型的属性分组
SELECT 
    id,
    bk_obj_id,
    bk_group_id,
    bk_group_name,
    bk_group_index,
    bk_isdefault,
    is_collapse,
    ispre,
    creator,
    modifier,
    create_time,
    last_time
FROM cc_PropertyGroup
WHERE bk_obj_id = :model_id
  AND bk_supplier_account = '0'
ORDER BY bk_group_index ASC
