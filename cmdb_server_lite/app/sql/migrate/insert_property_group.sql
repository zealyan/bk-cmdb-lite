-- 新建属性分组（2 处复用：按模型补全 default 分组 / 按属性实际引用反推补全）
-- 复用点先查 cc_PropertyGroup 是否已存在（见 migrate_property_groups），已存在则走
-- update_property_group.sql 原位刷新，故此处的纯 INSERT 是「缺失才补」语义。
-- bk_biz_id/creator/modifier 是固定字面量（无业务变量），沿用原内联写法，
-- 不占绑定参数；bk_supplier_account 同样固定 '0'。
INSERT INTO cc_PropertyGroup
    (_id, bk_obj_id, bk_group_id, bk_group_name, bk_group_index,
     bk_isdefault, is_collapse, ispre, bk_biz_id, bk_supplier_account,
     creator, modifier)
VALUES
    (:_id, :bk_obj_id, :bk_group_id, :bk_group_name, :bk_group_index,
     :bk_isdefault, :is_collapse, :ispre, 0, '0', 'admin', 'admin')
