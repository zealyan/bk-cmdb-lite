SELECT id, supplier, principal, res_type, obj_id, action, business_id, effect
FROM cc_AuthPolicy
WHERE (:supplier IS NULL OR supplier = :supplier)
  AND (:principal IS NULL OR principal = :principal)
  AND (:res_type IS NULL OR res_type = :res_type)
  AND (:obj_id IS NULL OR obj_id = :obj_id OR obj_id IS NULL)
  AND (:business_id IS NULL OR business_id = :business_id OR business_id IS NULL)
  AND (:action IS NULL OR action = :action)
ORDER BY id
