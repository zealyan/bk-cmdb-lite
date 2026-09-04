-- 原位更新属性分组元数据（按 id 定位，修正早期写入的显示名/序号/标志位）
-- 复用点先查 (bk_obj_id, bk_group_id) 命中 canonical id，再走本语句刷新；
-- 仅刷新规范列，不改绑定归属。modifier/last_time 固定字面量：
--   modifier='admin' 标记由迁移脚本统一维护，last_time=CURRENT_TIMESTAMP 落到当前时刻。
UPDATE cc_PropertyGroup
SET _id = :_id,
    bk_group_name = :bk_group_name,
    bk_group_index = :bk_group_index,
    bk_isdefault = :bk_isdefault,
    is_collapse = :is_collapse,
    ispre = :ispre,
    modifier = 'admin',
    bk_supplier_account = '0',
    last_time = CURRENT_TIMESTAMP
WHERE id = :id
