SELECT 
    oa.*,
    ad.bk_asst_name,
    ad.src_des,
    ad.dest_des,
    ad.direction
FROM cc_ObjAsst oa
JOIN cc_AsstDes ad ON oa.bk_asst_id = ad.bk_asst_id