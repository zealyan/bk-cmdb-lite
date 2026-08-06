export const BUILTIN_MODELS = {
  BUSINESS: 'biz',
  SET: 'set',
  MODULE: 'module',
  HOST: 'host',
  BUSINESS_SET: 'bk_biz_set_obj',
  PROJECT: 'bk_project'
}

export const HOST_MODEL_ID = 'host'

export const MODEL_ID_FIELD_MAP = {
  bk_biz_set_obj: { id: 'bk_biz_set_id', name: 'bk_biz_set_name' },
  biz: { id: 'bk_biz_id', name: 'bk_biz_name' },
  host: { id: 'bk_host_id', name: 'bk_host_name' },
  module: { id: 'bk_module_id', name: 'bk_module_name' },
  set: { id: 'bk_set_id', name: 'bk_set_name' },
  bk_project: { id: 'id', name: 'bk_project_name' }
}

export const getModelIdField = (modelId) => {
  return MODEL_ID_FIELD_MAP[modelId] || { id: 'bk_inst_id', name: 'bk_inst_name' }
}

export const getModelIdKey = (modelId) => {
  return getModelIdField(modelId).id
}

export const getModelNameKey = (modelId) => {
  return getModelIdField(modelId).name
}