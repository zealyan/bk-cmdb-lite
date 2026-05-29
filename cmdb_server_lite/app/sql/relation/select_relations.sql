SELECT 
    oa.bk_asst_id as bk_relation_type_id, 
    ad.bk_asst_name as bk_relation_type_name, 
    oa.bk_obj_id as bk_src_model, 
    oa.target_obj_id as bk_dst_model, 
    oa.cardinality
FROM cc_ObjAsst oa
JOIN cc_AsstDes ad ON oa.bk_asst_id = ad.bk_asst_id