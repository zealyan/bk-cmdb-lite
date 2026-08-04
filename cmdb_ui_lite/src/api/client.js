import axios from 'axios';

const baseURL = '/';

const http = axios.create({
  baseURL,
  timeout: 10000,
  withCredentials: false,
  headers: {
    'Content-Type': 'application/json'
  },
  paramsSerializer: (params) => {
    return Object.entries(params)
      .filter(([_, v]) => v !== undefined && v !== null && v !== '')
      .map(([k, v]) => {
        const encodedKey = encodeURIComponent(k);
        const encodedValue = encodeURIComponent(v);
        return `${encodedKey}=${encodedValue}`;
      })
      .join('&');
  }
})

// 基本 API 请求拦截器
http.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 统一处理原项目 BaseResp 格式
// 与原项目一致：成功时返回 data 字段，错误时抛出包含 bk_error_msg 的异常
http.interceptors.response.use(
  (response) => {
    const data = response.data
    // 如果响应格式符合原项目 BaseResp 格式（含 result 字段）
    if (data !== null && typeof data === 'object' && 'result' in data) {
      if (data.result === false) {
        // 业务错误：抛出异常，包含 bk_error_msg 和 bk_error_code
        const error = new Error(data.bk_error_msg || '业务处理失败')
        error.response = { data }
        return Promise.reject(error)
      }
      // 成功：返回 data 字段内容
      return data.data !== undefined ? data.data : data
    }
    // 非标准格式：直接返回原始数据（向后兼容）
    return data
  },
  (error) => {
    // HTTP 层错误（网络超时、状态码非 2xx 等）
    // 统一处理：若响应体符合 BaseResp 格式（含 result:false），提取 bk_error_msg
    // 作为错误信息，避免上层只拿到 "Request failed with status code 400" 这类传输层文案。
    const resp = error.response
    if (resp && resp.data && typeof resp.data === 'object'
        && 'result' in resp.data && resp.data.result === false) {
      const bizError = new Error(resp.data.bk_error_msg || '业务处理失败')
      bizError.response = resp
      bizError.bk_error_code = resp.data.bk_error_code
      bizError.isBusinessError = true
      return Promise.reject(bizError)
    }
    return Promise.reject(error)
  }
)

// 模型相关 API
export const modelAPI = {
  // 健康检查
  checkHealth () {
    return http.get('/api/v1/common/health')
  },

  // 获取所有分类
  listClassifications () {
    return http.get('/api/v1/classifications')
  },
  
  // 查询分类及其下属模型（对应原项目的 searchClassificationsObjects）
  searchClassificationsObjects () {
    return http.post('/api/v1/classifications/find/classificationobject')
  },
  
  // 获取所有模型
  listModels () {
    return http.get('/api/v1/models')
  },
  
  // 获取单个模型
  getModel (modelId) {
    return http.get(`/api/v1/models/${modelId}`)
  },

  // 更新模型元数据（停用/启用等）
  updateModel (modelId, data) {
    return http.put(`/api/v1/models/${modelId}`, { data })
  },

  // 获取模型属性
  getModelAttributes (modelId) {
    return http.get(`/api/v1/models/${modelId}/attributes`)
  },

  // 获取模型属性分组
  getModelPropertyGroups (modelId) {
    return http.get(`/api/v1/models/${modelId}/property-groups`)
  },
  
  // 获取模型实例列表
  listInstances (modelId, params = {}) {
    return http.get(`/api/v1/models/${modelId}/instances`, { params })
  },

  // 搜索模型实例 (使用POST避免URL编码问题)
  searchInstances (modelId, params = {}) {
    return http.post(`/api/v1/models/${modelId}/instances/search`, params)
  },
  
  // 获取单个实例
  getInstance (modelId, instanceId) {
    return http.get(`/api/v1/models/${modelId}/instances/${instanceId}`)
  },
  
  // 获取实例关联
  getInstanceAssociations (instanceId) {
    return http.get(`/api/v1/instances/${instanceId}/associations`)
  },
  
  // 获取关联实例详情
  getRelatedInstances (instanceId, modelId) {
    return http.get(`/api/v1/instances/${instanceId}/related`, { params: { model_id: modelId } })
  },
  
  // 获取所有关联关系
  listRelations () {
    return http.get('/api/v1/relations')
  },
  
  // 获取统计信息
  getStatistics () {
    return http.get('/api/v1/common/statistics')
  },

  // 按实例ID列表查询实例（使用搜索接口 + $in 条件）
  // 内置模型使用专用主键字段（如 host 用 bk_host_id），自定义模型用 bk_inst_id
  getInstancesByIds (modelId, ids = []) {
    const idFieldMap = {
      'host': 'bk_host_id',
      'biz': 'bk_biz_id',
      'set': 'bk_set_id',
      'module': 'bk_module_id',
      'bk_biz_set_obj': 'bk_biz_set_id'
    }
    const idField = idFieldMap[modelId] || 'bk_inst_id'
    return http.post(`/api/v1/models/${modelId}/instances/search`, {
      conditions: {
        condition: 'AND',
        rules: [{
          field: idField,
          operator: '$in',
          value: ids
        }]
      },
      page: {
        limit: ids.length,
        start: 0
      }
    })
  },

  // 检查实例的关联关系数量
  checkInstanceAssociations (modelId, ids = []) {
    return http.post(`/api/v1/models/${modelId}/instances/check-associations`, { ids })
  },

  // 校验实例数据的唯一性
  checkInstanceUnique (modelId, data, excludeInstanceId = null) {
    return http.post(`/api/v1/models/${modelId}/instances/check-unique`, {
      data,
      exclude_instance_id: excludeInstanceId
    })
  },

  // 删除实例（支持批量）
  deleteInstances (modelId, ids = []) {
    return http.delete(`/api/v1/models/${modelId}/instances`, { data: { ids } })
  },

  // 创建新实例
  createInstance (modelId, data) {
    return http.post(`/api/v1/models/${modelId}/instances`, { data })
  },

  // 更新单个实例
  updateInstance (modelId, instanceId, data) {
    // 与 createInstance 保持一致：后端 update_instance 读取 data.get('data', {}),
    // 必须将请求体包裹为 { data }，否则扁平 body 会被当成空 data，更新成为空操作。
    return http.put(`/api/v1/models/${modelId}/instances/${instanceId}`, { data })
  },

  // 批量更新实例（格式1：每个实例有不同数据）
  batchUpdateInstances (modelId, updates) {
    return http.put(`/api/v1/models/${modelId}/instances`, { update: updates })
  },

  // 批量更新实例（格式2：多个实例使用相同数据）
  batchUpdateInstancesWithSameData (modelId, ids, data) {
    return http.put(`/api/v1/models/${modelId}/instances`, { ids, data })
  },

  // 批量获取模型实例数量统计
  getInstanceCounts (objIds = []) {
    return http.post('/api/v1/models/instances/count', { obj_ids: objIds })
  },

  // 获取主机拓扑信息（业务拓扑下的主机详情）
  getHostTopology (hostId, bizId) {
    const params = {}
    if (bizId) params.bk_biz_id = bizId
    return http.get(`/api/v1/topo/host/${hostId}/topology`, { params })
  },

  // 查询模型的唯一约束
  searchObjectUnique (modelId) {
    return http.post(`/find/objectunique/object/${modelId}`, [])
  },

  // 创建模型的唯一约束
  createObjectUnique (modelId, keys) {
    return http.post(`/create/objectunique/object/${modelId}`, { keys })
  },

  // 更新模型的唯一约束
  updateObjectUnique (modelId, uniqueId, keys) {
    return http.put(`/update/objectunique/object/${modelId}/unique/${uniqueId}`, { keys })
  },

  // 删除模型的唯一约束
  deleteObjectUnique (modelId, uniqueId) {
    return http.post(`/delete/objectunique/object/${modelId}/unique/${uniqueId}`)
  }
}

export { default as userCustom } from './user-custom.js';
export default http
