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
      return res?.info || []
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
  }
}
