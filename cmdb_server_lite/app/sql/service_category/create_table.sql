CREATE TABLE IF NOT EXISTS cc_ServiceCategory (
    id                   BIGINT NOT NULL,
    bk_biz_id            BIGINT NOT NULL DEFAULT 0,
    name                 VARCHAR(255) NOT NULL,
    bk_root_id           BIGINT NOT NULL DEFAULT 0,
    bk_parent_id         BIGINT NOT NULL DEFAULT 0,
    bk_supplier_account  VARCHAR(64) NOT NULL DEFAULT '0',
    is_built_in          INTEGER NOT NULL DEFAULT 0,
    create_time          VARCHAR(64),
    last_time            VARCHAR(64),
    PRIMARY KEY (id)
)
