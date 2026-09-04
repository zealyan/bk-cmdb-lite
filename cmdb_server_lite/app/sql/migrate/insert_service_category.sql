-- 种子化内置默认服务分类（cc_ServiceCategory，2 处复用：一级 Default / 二级 Default）
-- 两处仅 bk_parent_id 不同（一级为 0、二级为一级 id），统一以 pid 参数表达；
-- bk_biz_id 固定 0（全局分类，非业务私有），is_built_in 固定 1。
-- 注意：本语句是纯 INSERT（调用方先查重，缺失才插入），冲突键经调用方去重保证幂等。
INSERT INTO cc_ServiceCategory
    (id, bk_biz_id, name, bk_root_id, bk_parent_id, bk_supplier_account,
     is_built_in, create_time, last_time)
VALUES
    (:id, 0, :name, :root, :pid, :s, 1, :t, :t)
