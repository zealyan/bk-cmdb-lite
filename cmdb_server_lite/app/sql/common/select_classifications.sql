-- 获取所有分类
SELECT * FROM cc_ObjClassification
WHERE bk_ishidden = FALSE OR bk_ishidden IS NULL
ORDER BY id
