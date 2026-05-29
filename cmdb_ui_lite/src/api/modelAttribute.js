import client from './client'

export default {
  async find(params = {}) {
    try {
      const bk_obj_id = params?.condition?.bk_obj_id
      const res = await client.get(`/api/v1/models/${bk_obj_id}/attributes`)
      console.log('[ModelAttributeAPI] find response:', res)
      return res || {}
    } catch (error) {
      console.error('[ModelAttributeAPI] find error:', error)
      throw error
    }
  },

  async getModelAttributes(objId) {
    try {
      const res = await client.get(`/api/v1/models/${objId}/attributes`)

      console.log('[ModelAttributeAPI] getModelAttributes response:', {
        objId,
        res
      })

      if (res && res.attributes) {
        return res.attributes
      }

      if (Array.isArray(res)) {
        return res
      }

      return []
    } catch (error) {
      console.error('[ModelAttributeAPI] getModelAttributes error:', error)
      throw error
    }
  }
}
