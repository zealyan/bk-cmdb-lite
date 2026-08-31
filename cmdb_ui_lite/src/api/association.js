import client from './client'

export default {
  async find(params = {}) {
    const res = await client.post('/find/instassociation', params)
    return res || {}
  },

  async findAll(params = {}) {
    const res = await client.post('/find/instassociation', params)
    return res?.info || []
  },

  async create(data) {
    return await client.post('/create/instassociation', data)
  },

  async delete(objId, id) {
    return await client.delete(`/delete/instassociation/${objId}/${id}`)
  },

  async getModelAssociations(modelId) {
    const res = await client.get(`/api/v1/models/${modelId}/associations`)
    return res?.associations || []
  },

  async findAssociationType() {
    try {
      const res = await client.post('/find/associationtype', {})
      // 与 findObjectAssociation 保持一致：后端 success_response(associations) 将列表置于 data，
      // 响应拦截器返回该数组；兼容 {info} 结构兜底
      return Array.isArray(res) ? res : (res?.data || res?.info || [])
    } catch (e) {
      return []
    }
  },

  async findObjectAssociation(params = {}) {
    try {
      const res = await client.post('/find/objectassociation', { condition: params })
      return Array.isArray(res) ? res : (res?.info || [])
    } catch (e) {
      return []
    }
  },

  async getRelatedInstances(instanceId, modelId = null) {
    const url = modelId 
      ? `/api/v1/instances/${instanceId}/related?model_id=${modelId}`
      : `/api/v1/instances/${instanceId}/related`
    const res = await client.get(url)
    return res?.related || []
  },

  // 新增关联弹框：候选目标实例查询（全部/已关联/未关联 筛选 + 条件 + 排序 + 分页 组合查询）
  async searchCandidates(params = {}) {
    const res = await client.post('/api/v1/associations/candidates', params)
    return res || {}
  }
}
