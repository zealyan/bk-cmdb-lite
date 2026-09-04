import http from './client'

const API_BASE = '/api/v1'

// 服务分类（ServiceCategory）相关 API
// 对应后端 app/api/v1/service_category.py：
//   GET    /service/category?bk_biz_id=&bk_supplier_account=   列表（扁平）
//   GET    /service/category/<id>                          查询单个分类（含一级/二级路径）
//   POST   /service/category                                创建（一级 / 二级）
//   PUT    /service/category/<id>                          重命名
//   DELETE /service/category/<id>                          删除（级联子分类）
export const serviceAPI = {
  /**
   * 查询某业务下的服务分类列表（扁平，前端按 bk_parent_id / bk_root_id 组装两级树）
   * @param {number} bizId 业务ID
   * @param {Object} params 额外参数（bk_supplier_account 等）
   * @returns {Promise<{info: Array, count: number}>}
   */
  getServiceCategories(bizId, params = {}) {
    return http.get(`${API_BASE}/service/category`, {
      params: { bk_biz_id: bizId, ...params }
    })
  },

  /**
   * 按 id 查询单个服务分类，含两级路径（first_level / second_level 名称）
   * 用于业务拓扑「节点信息」tab 展示模块所属服务分类：服务分类：一级 / 二级
   * @param {number} catId 分类ID（即模块 service_category_id）
   * @returns {Promise<{id, name, bk_parent_id, bk_root_id, first_level: {id,name}|null, second_level: {id,name}|null}>}
   */
  getServiceCategory(catId) {
    return http.get(`${API_BASE}/service/category/${catId}`)
  },

  /**
   * 创建服务分类
   * @param {number} bizId 业务ID
   * @param {Object} payload { name, bk_parent_id? }（bk_parent_id 缺省为一级分类）
   * @returns {Promise<{id, bk_biz_id, name, bk_root_id, bk_parent_id, bk_supplier_account, is_built_in}>}
   */
  createServiceCategory(bizId, payload = {}) {
    return http.post(`${API_BASE}/service/category`, { bk_biz_id: bizId, ...payload })
  },

  /**
   * 重命名服务分类
   * @param {number} catId 分类ID
   * @param {string} name 新名称
   * @returns {Promise<Object>}
   */
  updateServiceCategory(catId, name) {
    return http.put(`${API_BASE}/service/category/${catId}`, { name })
  },

  /**
   * 删除服务分类（级联删除其下子分类）
   * @param {number} catId 分类ID
   * @returns {Promise<{deleted: number}>}
   */
  deleteServiceCategory(catId) {
    return http.delete(`${API_BASE}/service/category/${catId}`)
  }
}

export default serviceAPI
