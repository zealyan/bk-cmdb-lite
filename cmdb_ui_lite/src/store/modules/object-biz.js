/**
 * objectBiz store —— 对齐原项目 bk-cmdb
 * （src/ui/src/store/modules/api/object-biz.js 的 bizId 切片）
 *
 * 原项目中业务 ID 的「数据绑定」中枢就是 store 里的 `bizId`：
 *  - 路由守卫（business-interceptor.before）在每次进入业务时
 *    `store.commit('objectBiz/setBizId', id)`；
 *  - 导航栏菜单链接（getMenuLink）用 `store.getters['objectBiz/bizId']` 生成业务路由；
 *  - 业务选择器的值由 `route.params.bizId` 推导（与 store 始终一致）。
 *
 * 这里仅保留 lite 需要的 bizId 状态/绑定部分，不引入原项目的权限/业务列表等无关逻辑。
 */
const state = {
  bizId: null
}

const getters = {
  bizId: state => state.bizId
}

const mutations = {
  setBizId(state, bizId) {
    state.bizId = bizId
  }
}

export default {
  namespaced: true,
  state,
  getters,
  mutations
}
