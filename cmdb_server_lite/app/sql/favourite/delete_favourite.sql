DELETE FROM cc_HostFavourite
WHERE id = :fav_id
  AND bk_user = :bk_user
  AND bk_supplier_account = :bk_supplier_account
  AND bk_biz_id = :bk_biz_id
