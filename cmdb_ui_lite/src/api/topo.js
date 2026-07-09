import axios from 'axios'

const API_BASE = '/api/v1'

// 拓扑相关API
export const topoAPI = {
  /**
   * 获取业务列表
   * @returns {Promise<Array>} 业务列表
   */
  async getBizList() {
    const response = await axios.get(`${API_BASE}/topo/biz`)
    return response.data
  },

  /**
   * 获取业务下的集群列表
   * @param {number} bizId 业务ID
   * @returns {Promise<Array>} 集群列表
   */
  async getSetList(bizId) {
    const response = await axios.get(`${API_BASE}/topo/biz/${bizId}/set`)
    return response.data
  },

  /**
   * 获取集群下的模块列表
   * @param {number} setId 集群ID
   * @param {number} bizId 业务ID
   * @returns {Promise<Array>} 模块列表
   */
  async getModuleList(setId, bizId) {
    const response = await axios.get(`${API_BASE}/topo/set/${setId}/module`, {
      params: { bk_biz_id: bizId }
    })
    return response.data
  },

  /**
   * 获取业务下的主机列表（带分页）
   * @param {number} bizId 业务ID
   * @param {Object} params 分页参数
   * @returns {Promise<Object>} { info: [], count: number }
   */
  async getBizHostList(bizId, params = {}) {
    const response = await axios.get(`${API_BASE}/topo/biz/${bizId}/host`, {
      params: {
        page: params.page || 1,
        page_size: params.page_size || 20,
        sort: params.sort || 'bk_host_id'
      }
    })
    return response.data
  },

  /**
   * 获取集群下的主机列表（带分页）
   * @param {number} setId 集群ID
   * @param {number} bizId 业务ID
   * @param {Object} params 分页参数
   * @returns {Promise<Object>} { info: [], count: number }
   */
  async getSetHostList(setId, bizId, params = {}) {
    const response = await axios.get(`${API_BASE}/topo/set/${setId}/host`, {
      params: {
        bk_biz_id: bizId,
        page: params.page || 1,
        page_size: params.page_size || 20,
        sort: params.sort || 'bk_host_id'
      }
    })
    return response.data
  },

  /**
   * 获取模块下的主机列表（带分页）
   * @param {number} moduleId 模块ID
   * @param {Object} params 分页参数
   * @returns {Promise<Object>} { info: [], count: number }
   */
  async getModuleHostList(moduleId, params = {}) {
    const response = await axios.get(`${API_BASE}/topo/module/${moduleId}/host`, {
      params: {
        page: params.page || 1,
        page_size: params.page_size || 20,
        sort: params.sort || 'bk_host_id'
      }
    })
    return response.data
  },

  /**
   * 获取业务拓扑树（完整树结构）
   * @returns {Promise<Array>} 拓扑树节点列表
   */
  async getBizTopoTree() {
    const response = await axios.get(`${API_BASE}/topo/tree`)
    return response.data
  }
}

export default topoAPI