export const BUILTIN_MODELS = {
  BUSINESS: 'biz',
  SET: 'set',
  MODULE: 'module',
  HOST: 'host',
  BUSINESS_SET: 'bk_biz_set_obj',
  PROJECT: 'bk_project'
}

export const HOST_MODEL_ID = 'host'

// 不能更新修改的字段（在可能发生编辑操作的页面里不显示出来）
// 对齐原项目 src/ui/src/dictionary/model-constants.js 的 BUILTIN_UNEDITABLE_FIELDS。
// 本项目的内置时间属性 create_time / last_time 与上游 bk_created_at / bk_updated_at
// 语义等价（后端 InstanceService / CLI 自动写入，isreadonly + editable=false），
// 因此同样纳入：详情页照常展示，新增 / 编辑 / 批量更新表单里不再出现空的禁用输入框。
export const BUILTIN_UNEDITABLE_FIELDS = [
  'bk_updated_by',
  'bk_updated_at',
  'bk_created_by',
  'bk_created_at',
  'create_time',
  'last_time'
]

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