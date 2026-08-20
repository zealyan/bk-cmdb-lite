CREATE TABLE IF NOT EXISTS cc_UserBase (
    bk_user_id          SERIAL PRIMARY KEY,
    bk_user_name        VARCHAR(255) NOT NULL UNIQUE,
    bk_supplier_account VARCHAR(64) NOT NULL DEFAULT '0',
    bk_role             INTEGER NOT NULL DEFAULT 2,
    bk_password         VARCHAR(512) NOT NULL,
    create_time         VARCHAR(64)
)
