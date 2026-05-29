import axios from 'axios';

const baseURL = '/';

const http = axios.create({
  baseURL,
  timeout: 10000,
  withCredentials: false,
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

// 响应拦截器
http.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API Error:', error)
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
  
  // 获取模型属性
  getModelAttributes (modelId) {
    return http.get(`/api/v1/models/${modelId}/attributes`)
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

  // 检查实例的关联关系数量
  checkInstanceAssociations (modelId, ids = []) {
    return http.post(`/api/v1/models/${modelId}/instances/check-associations`, { ids })
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
    return http.put(`/api/v1/models/${modelId}/instances/${instanceId}`, data)
  },

  // 批量更新实例（格式1：每个实例有不同数据）
  batchUpdateInstances (modelId, updates) {
    return http.put(`/api/v1/models/${modelId}/instances`, { update: updates })
  },

  // 批量更新实例（格式2：多个实例使用相同数据）
  batchUpdateInstancesWithSameData (modelId, ids, data) {
    return http.put(`/api/v1/models/${modelId}/instances`, { ids, data })
  }
}

export { default as userCustom } from './user-custom.js';
export default http
