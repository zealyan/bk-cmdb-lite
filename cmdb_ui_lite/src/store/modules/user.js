/**
 * 共享登录态模块（common / 公共显示）
 * ------------------------------------------------------------
 * 把「当前登录用户」提升为全应用唯一可信源，而非页头组件的局部 data。
 * 这样页头（CmdbHeader）及其他任意组件都能通过 getter 读取同一份登录态，
 * 不受路由页面切换、组件重挂的影响（即"不会被路由页面影响"）。
 *
 * 注意：本模块只持有展示态（用户名 / 是否免登录 / 是否已登录），
 * token 的存取仍在 src/auth.js（localStorage + cookie），二者通过
 * 登录页 / 页头 loadUser / 注销 三处同步。
 */
export default {
  namespaced: true,
  state: {
    userName: '',
    skipLogin: false,
    isLoggedIn: false
  },
  getters: {
    userName: (state) => state.userName,
    skipLogin: (state) => state.skipLogin,
    isLoggedIn: (state) => state.isLoggedIn
  },
  mutations: {
    /**
     * 写入登录用户。name 为空时回落为 ''（展示层用 v-if 隐藏登录信息）。
     * skipLogin=true 视为已登录（免登录模式，身份为 admin）。
     */
    setUser(state, payload = {}) {
      const { name, skipLogin } = payload
      state.userName = name || ''
      state.skipLogin = !!skipLogin
      state.isLoggedIn = !!state.userName
    },
    setLoggedIn(state, value) {
      state.isLoggedIn = !!value
    },
    clearUser(state) {
      state.userName = ''
      state.skipLogin = false
      state.isLoggedIn = false
    }
  }
}
