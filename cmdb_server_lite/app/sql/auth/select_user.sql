SELECT bk_user_id, bk_user_name, bk_supplier_account, bk_role, create_time
FROM cc_UserBase
WHERE bk_user_name = :name
