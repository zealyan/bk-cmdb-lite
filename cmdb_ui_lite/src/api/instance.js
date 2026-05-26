import client from './client'

export default {
  async find(objId, params = {}) {
    const res = await client.post(`/find/${objId}`, params)
    return res || {}
  },

  async findOne(objId, instId) {
    try {
      const res = await client.post(`/find/${objId}`, {
        condition: {
          bk_obj_id: objId,
          id: Number(instId)
        }
      })

      console.log('[InstanceAPI] findOne response:', res)

      if (res && typeof res === 'object' && res.id) {
        return res
      }

      return null
    } catch (error) {
      console.error('[InstanceAPI] findOne error:', error)
      throw error
    }
  },

  async getInstanceDetails(objId, instId) {
    try {
      const res = await client.post(`/find/${objId}`, {
        condition: {
          bk_obj_id: objId,
          id: Number(instId)
        }
      })

      console.log('[InstanceAPI] getInstanceDetails response:', res)

      if (res && typeof res === 'object' && res.id) {
        return res
      }

      return null
    } catch (error) {
      console.error('[InstanceAPI] getInstanceDetails error:', error)
      throw error
    }
  }
}
