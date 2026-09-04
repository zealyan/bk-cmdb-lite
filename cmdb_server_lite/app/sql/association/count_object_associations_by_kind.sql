-- 统计某关联类型被多少个「模型关联」引用
-- 对齐上游 logics/model/association.go:113-127：已被使用的关联类型禁止删除
-- （上游用 GetCountByFilter 查 cc_ObjAsst 中 bk_asst_id = 该类型的记录数）
SELECT COUNT(*) AS cnt
FROM cc_ObjAsst
WHERE bk_asst_id = :bk_asst_id
  AND bk_supplier_account = :bk_supplier_account
