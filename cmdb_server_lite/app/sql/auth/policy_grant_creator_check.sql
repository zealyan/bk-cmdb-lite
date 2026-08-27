SELECT id
FROM cc_AuthPolicy
WHERE supplier = :s
  AND principal = :p
  AND res_type = 'modelInstance'
  AND obj_id = :o
  AND action = :a
