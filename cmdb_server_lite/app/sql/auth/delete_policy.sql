DELETE FROM cc_AuthPolicy
WHERE (:id IS NULL OR id = :id)
  AND (:supplier IS NULL OR supplier = :supplier)
  AND (:principal IS NULL OR principal = :principal)
  AND (:res_type IS NULL OR res_type = :res_type)
  AND (:obj_id IS NULL OR obj_id = :obj_id)
  AND (:business_id IS NULL OR business_id = :business_id)
  AND (:action IS NULL OR action = :action)
