import http, { withCancelToken } from './client'

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
  async getInstanceTopo(bizId, params = {}, config = {}) {
    const response = await http.get(`${API_BASE}/topo/instance/mainline`,
      withCancelToken({
        params: {
          bk_biz_id: bizId,
          with_statistics: params.with_statistics || true,
          ...params
        }
      }, config))
    return response
  },

  /**
   * 获取主线实例某父节点的直接子层（分层懒加载）
   *
   * 对齐原项目前端 business-topology 的 lazy-method 分层加载思想：不再一次性返回
   * 整棵 13 万节点树（34MB 响应），而是按父节点逐层懒加载，每层响应仅几百 KB，
   * 彻底避免大响应在受限网络/网关下的传输超时。
   *
   * @param {number} bizId 业务ID
   * @param {string} parentObjId 父节点模型ID（biz/set/module/sys/subsys...）
   * @param {number} parentInstId 父节点实例ID
   * @param {boolean} withStatistics 是否返回聚合主机数 count
   * @returns {Promise<Array>} 子节点列表 [{bk_obj_id, bk_inst_id, bk_inst_name, default, count, is_leaf}]
   */
  async getInstanceChildren(bizId, parentObjId, parentInstId, withStatistics = true) {
    const response = await http.get(`${API_BASE}/topo/instance/children`, {
      params: {
        bk_biz_id: bizId,
        bk_obj_id: parentObjId,
        bk_inst_id: parentInstId,
        with_statistics: withStatistics
      }
    })
    return response
  },

  /**
   * 批量查询主线实例的祖先路径（biz→...→当前实例）
   *
   * 对齐原项目 find/topopath/biz/{bizId}。懒加载树初始只有业务根节点，
   * 转移对话框 / 主拓扑树按 URL node 恢复深层选中时，用此接口拿目标实例的
   * 完整主线路径（支持任意自定义主线层），再逐级展开树节点。
   *
   * @param {number} bizId 业务ID
   * @param {Array<number>} instIds 实例ID列表
   * @param {string} [supplierAccount] 供应商账号，默认 '0'
   * @param {string} [objId] 起始模型ID，默认 'module'（biz/set/sys/自定义层均可）
   * @returns {Promise<Array>} 与入参顺序一一对应的路径数组 [[{bk_obj_id, bk_inst_id, bk_inst_name}...], ...]
   */
  async getInstancePath(bizId, instIds, supplierAccount = '0', objId = 'module') {
    const ids = Array.isArray(instIds) ? instIds.join(',') : String(instIds || '')
    const response = await http.get(`${API_BASE}/topo/instance/path`, {
      params: {
        bk_biz_id: bizId,
        bk_inst_id: ids,
        bk_obj_id: objId,
        bk_supplier_account: supplierAccount
      }
    })
    return response
  },

  /**
   * 获取拓扑节点统计数据（批量，复刻原项目 getTopoStatistics）
   * @param {number} bizId 业务ID
   * @param {Object} params 参数 { condition: [{bk_obj_id, bk_inst_id}] }
   * @param {Object} [config] 请求取消配置 { requestId, cancelPrevious }
   *        复刻上游拓扑树：节点快速展开/切换时，用 requestId 取消上一批未完成的统计请求，
   *        避免陈旧统计结果在竞态下回写节点状态（status/host_count），造成数量标签闪烁。
   *
   * 优化模式（对齐原项目 store/modules/api/object-main-line-module.js getTopoStatistics）：
   * 原项目后端强制单请求 condition 上限 1000（BKParamMaxLength），前端按 1000 个节点
   * 分片 + Promise.all 并发；lite 此处同构复刻——整个批量共用一个 requestId 取消令牌
   * （分片间共享 cancelToken，避免互相取消），全部并发、结果合并后一次性返回。
   * @returns {Promise<Array>} 统计结果列表
   */
  async getTopoStatistics(bizId, params = {}, config = {}) {
    const condition = (params && params.condition) || []
    const limit = 1000
    // 一个批量共用一个取消令牌：cancelPrevious 只取消"上一批"，分片之间互不干扰
    const baseConfig = withCancelToken({}, config)
    const queue = []
    for (let i = 0; i < condition.length; i += limit) {
      queue.push(http.post(`${API_BASE}/topo/statistics`, {
        bk_biz_id: bizId,
        condition: condition.slice(i, i + limit)
      }, baseConfig))
    }
    const results = await Promise.all(queue)
    return results.reduce((acc, cur) => acc.concat(cur), [])
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
  async searchHosts(payload = {}, config = {}) {
    const response = await http.post(`${API_BASE}/topo/hosts/search`, payload,
      withCancelToken({}, config))
    return response
  },

  /**
   * 获取转移"业务模块"所需的业务拓扑树（集群分类 + 模块分类，含 default 标识）
   *
   * 对应原项目: POST find/topoinst/biz/{bizId}
   * 返回结构区分集群(set)与模块(module)分类，default 字段标识空闲机池/内部模块：
   *   0 普通 / 1 空闲机 / 2 故障机 / 3 待回收（set 级 default=1 即空闲机池）
   *
   * @param {number} bizId 业务ID
   * @param {Object} params 额外参数（bk_supplier_account 等）
   * @returns {Promise<Array>} 业务拓扑树（单根节点数组）
   */
  async getInstTopo(bizId, params = {}) {
    const response = await http.post(`${API_BASE}/host/transfer/topology/biz/${bizId}`, params)
    return response
  },

  /**
   * 获取空闲机池（转移到空闲模块使用）
   *
   * 对应原项目: GET topo/internal/{supplierAccount}/{bizId}/with_statistics
   *
   * @param {string} supplierAccount 供应商账号，默认 '0'
   * @param {number} bizId 业务ID
   * @returns {Promise<Object>} { bk_set_id, bk_set_name, module: [{ bk_module_id, bk_module_name, default }] }
   */
  async getInternalTopo(supplierAccount, bizId) {
    const response = await http.get(`${API_BASE}/host/transfer/internal/${supplierAccount}/${bizId}`)
    return response
  },

  /**
   * 查询指定主机的模块绑定关系（cc_ModuleHostConfig）
   * 用于转移前预选主机当前所属模块，作为写操作的上下文依据。
   *
   * @param {number} bizId 业务ID
   * @param {Array<number>} hostIds 主机ID列表（为空则返回该业务全部绑定）
   * @param {Object} params 额外参数（bk_supplier_account 等）
   * @returns {Promise<Array>} 绑定关系列表
   */
  async getHostModuleConfig(bizId, hostIds = [], params = {}) {
    const response = await http.get(`${API_BASE}/host/transfer/host/modules`, {
      params: {
        bk_biz_id: bizId,
        bk_host_id: Array.isArray(hostIds) ? hostIds.join(',') : (hostIds || ''),
        ...params
      }
    })
    return response
  },

  /**
   * 执行主机转移写操作（修改 cc_ModuleHostConfig 绑定）
   *
   * 对应原项目: src/source_controller/coreservice/core/host/transfer/
   * 语义：先删除该主机在当前业务内的所有模块绑定，再写入新选的目标模块绑定；
   *       若转移后主机无任何模块绑定，自动挂到空闲机(default=1)模块。
   *
   * @param {Object} payload 转移请求
   * @param {number} payload.bk_biz_id 业务ID
   * @param {Array<number>} payload.bk_host_id 待转移主机ID列表
   * @param {Array<number>} payload.module_id 目标模块ID列表
   * @param {string} payload.transfer_type 'business' | 'idle'
   * @param {string} [payload.bk_supplier_account] 供应商账号，默认 '0'
   * @returns {Promise<Object>} { result, code, message, data: { transferred_hosts, target_modules, transfer_type } }
   */
  async transferModules(payload = {}) {
    const response = await http.post(`${API_BASE}/host/transfer/modules`, payload)
    return response
  },

  /**
   * 执行跨业务主机转移（源业务 A → 目标业务 B 的指定模块）
   *
   * 对应原项目: POST /hosts/modules/across/biz（TransferHostAcrossBusiness）
   * 语义：解除源业务下这些主机的全部模块绑定，再在目标业务指定模块建立绑定
   *       （绑定记录 bk_biz_id 写为目标业务）。
   *
   * @param {Object} payload 跨业务转移请求
   * @param {number} payload.src_bk_biz_id 源业务ID（主机当前所属业务）
   * @param {number} payload.dst_bk_biz_id 目标业务ID（主机转移后的归属业务）
   * @param {Array<number>} payload.bk_host_id 待转移主机ID列表
   * @param {Array<number>} payload.module_id 目标业务下的目标模块ID列表
   * @param {string} [payload.bk_supplier_account] 供应商账号，默认 '0'
   * @returns {Promise<Object>} { result, code, message, data: { transferrd_hosts, target_biz, target_modules } }
   */
  async transferAcrossBiz(payload = {}) {
    const response = await http.post(`${API_BASE}/host/transfer/modules/across/biz`, payload)
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
  },

  /**
   * 获取主线模型顺序（权威来源，决定"某节点下应创建哪一层"）
   *
   * 对应后端 GET /topo/model/mainline（SearchMainlineModelTopo）。
   * 返回主线模型树，前端扁化为最左路径顺序，如 ['biz','appsys','set','module']。
   * 点击节点的"新建"应创建其在主线中的【直接子层】，而非写死 biz→set，
   * 从而严格维持 biz→appsys→zone→set→module 等任意主线顺序。
   *
   * @returns {Promise<string[]>} 主线模型顺序（bk_obj_id 列表）
   */
  async getMainlineModelTree() {
    const response = await http.get(`${API_BASE}/topo/model/mainline`)
    const data = response && (response.data || response) || {}
    // 递归提取最左路径（leftest_object_id_list）
    const flatten = (node) => {
      if (!node) return []
      return [node.bk_obj_id, ...flatten((node.children || [])[0])].filter(Boolean)
    }
    return flatten(data)
  },

  /**
   * 在主线某父实例下创建任意层级的子实例（通用，替代专用 createSet/createModule）
   *
   * 对应后端 POST /topo/instance/mainline（包装 topo_service.create_mainline_instance）。
   * 由后端按主线顺序设置 bk_parent_id（指向父实例）与 bk_biz_id（继承父实例），
   * 不会在 biz 下错建 set。
   *
   * @param {Object} payload
   * @param {string} payload.parent_obj_id 父模型ID（点击节点所属模型，如 'biz'）
   * @param {number} payload.parent_inst_id 父实例ID（点击节点实例ID）
   * @param {string} payload.model_id 待创建子模型ID（父的直接子主线层，如 'appsys'）
   * @param {string[]} payload.names 实例名称列表（批量）
   * @param {number} [payload.bk_biz_id] 业务ID（父为 biz 时即 parent_inst_id；可缺省）
   * @param {Object} [payload.attrs] 自定义层额外属性
   * @returns {Promise<Object>} { result, data: { created: [...], error_names: [...] } }
   */
  async createMainlineInstance(payload = {}) {
    const response = await http.post(`${API_BASE}/topo/instance/mainline`, payload)
    return response
  },

  /**
   * 删除拓扑节点（set/module）
   * 复刻原项目：删除前会检查是否有主机关联，有则拒绝删除
   * @param {string} objId 模型ID（set/module）
   * @param {number} instId 实例ID
   * @param {Object} params 额外参数（bk_biz_id 等）
   * @returns {Promise<Object>}
   */
  async deleteNode(objId, instId, params = {}) {
    const response = await http.delete(`${API_BASE}/topo/node/${objId}/${instId}`, {
      params
    })
    return response
  }
}

export default topoAPI