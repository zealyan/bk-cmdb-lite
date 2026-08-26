DELETE FROM cc_AuthPolicy
WHERE principal = :principal
  AND (:supplier IS NULL OR supplier = :supplier)
