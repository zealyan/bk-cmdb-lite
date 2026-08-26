CREATE TABLE IF NOT EXISTS cc_HostFavourite (
    id                  VARCHAR(64) PRIMARY KEY,
    bk_user             VARCHAR(255) NOT NULL,
    bk_supplier_account VARCHAR(64) NOT NULL DEFAULT '0',
    bk_biz_id           BIGINT NOT NULL DEFAULT 0,
    name                VARCHAR(255),
    info                TEXT,
    query_params        TEXT,
    is_default          INTEGER NOT NULL DEFAULT 0,
    count               INTEGER NOT NULL DEFAULT 0,
    type                VARCHAR(32) NOT NULL DEFAULT 'tradition',
    create_time         VARCHAR(64),
    last_time           VARCHAR(64)
)
