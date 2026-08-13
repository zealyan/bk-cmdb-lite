SELECT effect
FROM cc_AuthPolicy
WHERE supplier = :supplier
  AND principal = :principal
  AND res_type = :res_type
  AND (obj_id = :obj_id OR obj_id IS NULL)
  AND (business_id = :business_id OR business_id IS NULL)
  AND action IN (__ACTIONS__)
LIMIT 1
