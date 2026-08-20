UPDATE cc_HostFavourite
SET name = :name,
    query_params = :query_params,
    info = :info,
    type = :type,
    last_time = :last_time
WHERE id = :fav_id
  AND bk_user = :bk_user
  AND bk_supplier_account = :bk_supplier_account
  AND bk_biz_id = :bk_biz_id
