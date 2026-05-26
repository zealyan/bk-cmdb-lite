import api from './client'

export default {
  /**
   * 获取用户配置
   * @param {Object} config 请求配置
   * @param {string} config.userName 可选，用户名，默认使用admin
   * @returns {Promise} 返回用户配置对象
   */
  searchUserCustom(config = {}) {
    return api.post('/api/usercustom/user/search', {}, config)
  },

  /**
   * 保存用户配置
   * @param {Object} usercustom 配置数据
   * @param {Object} config 请求配置
   * @param {string} config.userName 可选，用户名，默认使用admin
   * @returns {Promise} 返回保存结果
   */
  saveUsercustom(usercustom, config = {}) {
    return api.post('/api/usercustom', usercustom, config)
  },

  /**
   * 获取模型列配置
   * @param {string} objId 模型ID
   * @param {Object} config 请求配置
   * @param {string} config.userName 可选，用户名，默认使用admin
   * @returns {Promise} 返回列配置数组
   */
  getModelCustomColumns(objId, config = {}) {
    return api.get(`/api/usercustom/model/${objId}`, config)
  },

  /**
   * 保存模型列配置
   * @param {string} objId 模型ID
   * @param {Array} columns 列配置数组
   * @param {Object} config 请求配置
   * @param {string} config.userName 可选，用户名，默认使用admin
   * @returns {Promise} 返回保存结果
   */
  saveModelCustomColumns(objId, columns, config = {}) {
    return api.post(`/api/usercustom/model/${objId}`, { columns }, config)
  },

  /**
   * 获取用户列表
   * @returns {Promise} 返回用户列表
   */
  listUsers() {
    return api.get('/api/users')
  }
}
