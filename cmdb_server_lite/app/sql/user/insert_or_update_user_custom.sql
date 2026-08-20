INSERT INTO user_custom (user_name, config_key, config_value, updated_at, bk_supplier_account)
VALUES (:user_name, :config_key, :config_value, :updated_at, :supplier)
ON CONFLICT(user_name, config_key, bk_supplier_account)
DO UPDATE SET config_value = excluded.config_value, updated_at = excluded.updated_at, bk_supplier_account = excluded.bk_supplier_account
