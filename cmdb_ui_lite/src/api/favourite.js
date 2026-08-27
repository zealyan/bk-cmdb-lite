import api from './client'

/**
 * 业务拓扑-主机列表「已收藏的条件」API（HostFavourite，对应后端 /api/v1/hosts/favorites）。
 *
 * 后端隔离维度（user / bk_supplier_account 由服务端从登录身份注入，bk_biz_id 随请求携带），
 * 因此前端只需在列表/删除时带上当前业务 bk_biz_id（取 FilterStore.bk_biz_id），
 * 创建时把当前筛选条件序列化进 query_params 即可，无需关心租户维度。
 *
 * 与 user-custom.js 一致：通过 client.js 的 axios 实例发起请求，
 * 请求拦截器自动注入 Authorization: Bearer <bk_token>，响应拦截器统一返回 data.data。
 */
export default {
  /**
   * 查询当前用户 + 本租户 + 本业务的收藏列表
   * @param {number} bkBizId 业务 ID（默认 0 = 全部）
   * @returns {Promise<Array>} 收藏项数组，每项含 { id, name, query_params, ... }
   */
  listFavourites(bkBizId = 0) {
    return api.get('/api/v1/hosts/favorites', { params: { bk_biz_id: bkBizId } })
      .then((res) => (res && Array.isArray(res.info)) ? res.info : [])
  },

  /**
   * 创建收藏条件
   * @param {Object} payload { name, query_params, bk_biz_id, type, ... }
   * @returns {Promise<Object>} 新建的收藏项（含后端生成的 id）
   */
  createFavourite(payload = {}) {
    return api.post('/api/v1/hosts/favorites', payload)
  },

  /**
   * 删除收藏（后端按 id + 三层隔离条件删除，无权则返回错误码）
   * @param {string|number} id 收藏 ID
   * @param {number} bkBizId 业务 ID（默认 0）
   * @returns {Promise}
   */
  deleteFavourite(id, bkBizId = 0) {
    return api.delete(`/api/v1/hosts/favorites/${id}`, { params: { bk_biz_id: bkBizId } })
  },

  /**
   * 更新收藏条件（对齐上游 put hosts/favorites/:id）
   * @param {string|number} id 收藏 ID
   * @param {Object} payload { name, query_params, bk_biz_id, type }
   * @returns {Promise}
   */
  updateFavourite(id, payload = {}) {
    return api.put(`/api/v1/hosts/favorites/${id}`, payload)
  }
}
