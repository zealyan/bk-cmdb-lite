-- 分页查询通用 SQL
-- 参数: :page 页码, :page_size 每页数量

SELECT * FROM {table_name}
WHERE 1=1
{{if conditions}}
  AND {{conditions}}
{{endif}}
ORDER BY id DESC
LIMIT :page_size OFFSET :offset
