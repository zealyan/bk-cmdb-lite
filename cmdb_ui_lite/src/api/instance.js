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

      const idFieldMap = {
        'biz': 'bk_biz_id',
        'set': 'bk_set_id',
        'module': 'bk_module_id',
        'host': 'bk_host_id',
        'bk_host': 'bk_host_id'
      }
      const idField = idFieldMap[objId] || 'bk_inst_id'

      if (res && typeof res === 'object' && (res.id || res[idField])) {
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

      const idFieldMap = {
        'biz': 'bk_biz_id',
        'set': 'bk_set_id',
        'module': 'bk_module_id',
        'host': 'bk_host_id',
        'bk_host': 'bk_host_id'
      }
      const idField = idFieldMap[objId] || 'bk_inst_id'

      if (res && typeof res === 'object' && (res.id || res[idField])) {
        return res
      }

      return null
    } catch (error) {
      console.error('[InstanceAPI] getInstanceDetails error:', error)
      throw error
    }
  }
}
