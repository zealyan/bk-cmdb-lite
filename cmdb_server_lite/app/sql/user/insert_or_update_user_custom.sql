INSERT INTO user_custom (user_name, config_key, config_value, updated_at)
VALUES (:user_name, :config_key, :config_value, :updated_at)
ON CONFLICT(user_name, config_key) 
DO UPDATE SET config_value = excluded.config_value, updated_at = excluded.updated_at