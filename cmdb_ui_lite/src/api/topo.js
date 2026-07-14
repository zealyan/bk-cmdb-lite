import http from './client'

const API_BASE = '/api/v1'

// 拓扑相关API
export const topoAPI = {
  /**
   * 获取业务列表
   * @returns {Promise<Array>} 业务列表
   */
  async getBizList() {
    const response = await http.get(`${API_BASE}/topo/biz`)
    return response
  },

  /**
   * 获取实例拓扑树（完整树，含统计）
   * @param {number} bizId 业务ID
   * @param {Object} params 参数（with_statistics 等）
   * @returns {Promise<Object>} 拓扑树数据
   */
  async getInstanceTopo(bizId, params = {}) {
    const response = await http.get(`${API_BASE}/topo/instance/mainline`, {
      params: {
        bk_biz_id: bizId,
        with_statistics: params.with_statistics || true,
        ...params
      }
    })
    return response
  },

  /**
   * 获取拓扑节点统计数据（批量）
   * @param {number} bizId 业务ID
   * @param {Object} params 参数
   * @returns {Promise<Array>} 统计结果列表
   */
  async getTopoStatistics(bizId, params = {}) {
    const response = await http.post(`${API_BASE}/topo/statistics`, {
      bk_biz_id: bizId,
      ...params
    })
    return response
  },

  /**
   * 获取业务下的集群列表（懒加载下一级）
   * @param {number} bizId 业务ID
   * @returns {Promise<Array>} 集群列表
   */
  async getBizSetList(bizId) {
    const response = await http.get(`${API_BASE}/topo/biz/${bizId}/set`, {
      params: { with_statistics: true }
    })
    return response
  },

  /**
   * 获取集群下的模块列表（懒加载下一级）
   * @param {number} setId 集群ID
   * @param {number} bizId 业务ID
   * @returns {Promise<Array>} 模块列表
   */
  async getSetModuleList(setId, bizId) {
    const response = await http.get(`${API_BASE}/topo/set/${setId}/module`, {
      params: { bk_biz_id: bizId, with_statistics: true }
    })
    return response
  },

  /**
   * 获取节点的主机数量统计
   * @param {string} objId 模型ID（biz/set/module）
   * @param {number} instId 实例ID
   * @param {Object} extra 额外参数（bk_biz_id 等）
   * @returns {Promise<{data: {count: number}}>}
   */
  async getNodeCount(objId, instId, extra = {}) {
    const response = await http.get(`${API_BASE}/topo/count`, {
      params: {
        bk_obj_id: objId,
        bk_inst_id: instId,
        ...extra
      }
    })
    return response
  },

  /**
   * 获取业务下的主机列表（带分页）
   * @param {number} bizId 业务ID
   * @param {Object} params 分页参数
   * @returns {Promise<Object>} { info: [], count: number }
   */
  async getBizHostList(bizId, params = {}) {
    const response = await http.get(`${API_BASE}/topo/biz/${bizId}/host`, {
      params: {
        page: params.page || 1,
        page_size: params.page_size || 20,
        sort: params.sort || 'bk_host_id'
      }
    })
    return response
  },

  /**
   * 获取集群下的主机列表（带分页）
   * @param {number} setId 集群ID
   * @param {number} bizId 业务ID
   * @param {Object} params 分页参数
   * @returns {Promise<Object>} { info: [], count: number }
   */
  async getSetHostList(setId, bizId, params = {}) {
    const response = await http.get(`${API_BASE}/topo/set/${setId}/host`, {
      params: {
        bk_biz_id: bizId,
        page: params.page || 1,
        page_size: params.page_size || 20,
        sort: params.sort || 'bk_host_id'
      }
    })
    return response
  },

  /**
   * 获取模块下的主机列表（带分页）
   * @param {number} moduleId 模块ID
   * @param {Object} params 分页参数
   * @returns {Promise<Object>} { info: [], count: number }
   */
  async getModuleHostList(moduleId, params = {}) {
    const response = await http.get(`${API_BASE}/topo/module/${moduleId}/host`, {
      params: {
        page: params.page || 1,
        page_size: params.page_size || 20,
        sort: params.sort || 'bk_host_id'
      }
    })
    return response
  },

  /**
   * 获取业务拓扑树（完整树结构）
   * @returns {Promise<Array>} 拓扑树节点列表
   */
  async getBizTopoTree() {
    const response = await http.get(`${API_BASE}/topo/tree`)
    return response
  },

  /**
   * 主机搜索（与原项目 HostCommonSearch 一致的 POST 接口）
   *
   * 对应原项目: POST /findmany/hosts/search/with_biz
   *
   * @param {Object} payload HostCommonSearch 请求载荷
   * @param {number} payload.bk_biz_id 业务ID
   * @param {Object} [payload.ip] IP搜索条件 { data: [], exact: 1, flag: 'bk_host_innerip|bk_host_outerip' }
   * @param {Array} [payload.condition] 多对象条件数组 [{ bk_obj_id, fields, condition: [{ field, operator, value }] }]
   * @param {Object} [payload.page] 分页 { start: 0, limit: 20, sort: 'bk_host_id' }
   * @returns {Promise<Object>} { result, data: { info: [], count: number }, code, message }
   */
  async searchHosts(payload = {}) {
    const response = await http.post(`${API_BASE}/topo/hosts/search`, payload)
    return response
  },

  /**
   * 创建集群
   * @param {number} bizId 业务ID
   * @param {Object} data 创建数据 { names: string[] }
   * @returns {Promise<Object>} { result: true, data: { created: [...] }, code: 0 }
   */
  async createSet(bizId, data) {
    const response = await http.post(`${API_BASE}/topo/biz/${bizId}/set`, data)
    return response
  },

  /**
   * 创建模块
   * @param {number} bizId 业务ID
   * @param {number} setId 集群ID
   * @param {Object} data 创建数据 { names: string[] }
   * @returns {Promise<Object>} { result: true, data: { created: [...] }, code: 0 }
   */
  async createModule(bizId, setId, data) {
    const response = await http.post(`${API_BASE}/topo/set/${setId}/module`, data)
    return response
  }
}

export default topoAPI