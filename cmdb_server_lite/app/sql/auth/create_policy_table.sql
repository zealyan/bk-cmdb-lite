CREATE TABLE IF NOT EXISTS cc_AuthPolicy (
    id          SERIAL PRIMARY KEY,
    supplier    VARCHAR(64) NOT NULL,
    principal   VARCHAR(255) NOT NULL,
    res_type    VARCHAR(64) NOT NULL,
    obj_id      VARCHAR(255),
    action      VARCHAR(64) NOT NULL,
    business_id VARCHAR(64),
    effect      VARCHAR(32) NOT NULL DEFAULT 'allow'
)
