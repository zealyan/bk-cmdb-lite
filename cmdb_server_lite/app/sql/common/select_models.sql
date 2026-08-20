-- 获取所有模型
SELECT * FROM cc_ObjDes
WHERE COALESCE(bk_ispaused, 0) != 1
ORDER BY obj_sort_number, bk_obj_id
