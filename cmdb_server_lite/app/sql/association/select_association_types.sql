-- 关联类型列表（cc_AsstDes）
-- 显式列出字段而非 SELECT *：保证多方言下列集合与顺序稳定，
-- 且后续新增物理列不会意外泄漏到接口响应。
-- 排序按 id 升序，使前端下拉顺序稳定（id 1..7 为 migrate 种子的预置类型，
-- 自建类型 id 由 generate_id 产生，数值更大，自然排在预置之后）。
SELECT id,
       bk_asst_id,
       bk_asst_name,
       bk_asst_icon,
       src_des,
       dest_des,
       direction,
       ispre,
       creator,
       modifier,
       create_time,
       last_time,
       bk_supplier_account
FROM cc_AsstDes
WHERE bk_supplier_account = :bk_supplier_account
ORDER BY id ASC
