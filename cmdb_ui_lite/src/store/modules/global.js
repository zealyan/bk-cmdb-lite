const state = {
  appHeight: window.innerHeight,
  noticeHeight: 0
}

const mutations = {
  setAppHeight(state, height) {
    state.appHeight = Math.max(0, Number(height) - Number(state.noticeHeight) || 0)
  },
  setNoticeHeight(state, height) {
    state.noticeHeight = Math.max(0, Number(height) || 0)
  }
}

const actions = {
  updateAppHeight({ commit }, height) {
    commit('setAppHeight', height)
  },
  updateNoticeHeight({ commit }, height) {
    commit('setNoticeHeight', height)
  }
}

const getters = {
  appHeight: (state) => state.appHeight,
  noticeHeight: (state) => state.noticeHeight
}

export default {
  namespaced: false,
  state,
  mutations,
  actions,
  getters
}
