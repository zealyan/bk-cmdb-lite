-- 修改用户密码（仅更新 bk_password，按 用户名 + 供应商账户 定位）
-- 占位符为命名参数，由 executor 做 SQLAlchemy 参数化；方言经 sqlglot 转译。
UPDATE cc_UserBase
SET bk_password = :bk_password
WHERE bk_user_name = :bk_user_name
  AND bk_supplier_account = :bk_supplier_account;
