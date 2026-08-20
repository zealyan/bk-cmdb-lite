SELECT id, bk_user, bk_supplier_account, bk_biz_id, name, info, query_params,
       is_default, count, type, create_time, last_time
FROM cc_HostFavourite
WHERE bk_user = :bk_user
  AND bk_supplier_account = :bk_supplier_account
  AND bk_biz_id = :bk_biz_id
ORDER BY last_time DESC
