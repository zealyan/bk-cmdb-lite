import client from './client'

export default {
  async find(params = {}) {
    const res = await client.post('/find/instassociation', params)
    console.log('association.find response:', res)
    return res || {}
  },

  async findAll(params = {}) {
    const res = await client.post('/find/instassociation', params)
    return res?.info || []
  },

  async create(data) {
    console.log('[API] association.create called with:', data)
    const res = await client.post('/create/instassociation', data)
    console.log('[API] association.create raw response:', res)
    console.log('[API] association.create response type:', typeof res, res instanceof Object)
    // client 的响应拦截器已经返回了 response.data，所以这里直接返回 res
    return res
  },

  async delete(objId, id) {
    const res = await client.delete(`/delete/instassociation/${objId}/${id}`)
    return res || res
  },

  async getModelAssociations(modelId) {
    const res = await client.get(`/api/models/${modelId}/associations`)
    return res?.associations || []
  },

  async findAssociationType() {
    try {
      const res = await client.post('/find/associationtype', {})
      console.log('[API] findAssociationType response:', res)
      console.log('[API] Response type:', typeof res, res instanceof Object)
      return res?.info || []
    } catch (e) {
      console.error('[API] findAssociationType error:', e)
      return []
    }
  },

  async findObjectAssociation(params = {}) {
    try {
      const res = await client.post('/find/objectassociation', { condition: params })
      console.log('[API] findObjectAssociation response:', res)
      console.log('[API] Response type:', typeof res, Array.isArray(res))
      return Array.isArray(res) ? res : (res?.info || [])
    } catch (e) {
      console.error('[API] findObjectAssociation error:', e)
      return []
    }
  },

  async getRelatedInstances(instanceId, modelId = null) {
    const url = modelId 
      ? `/api/instances/${instanceId}/related?model_id=${modelId}`
      : `/api/instances/${instanceId}/related`
    const res = await client.get(url)
    return res?.related || []
  }
}
