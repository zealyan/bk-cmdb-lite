SELECT bk_user_name,
       bk_supplier_account,
       bk_role
FROM cc_UserBase
WHERE bk_user_name = :bk_user_name
