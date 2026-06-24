const state = {
  appHeight: window.innerHeight,
  noticeHeight: 0,
  navStick: false,
  navFold: true,
  title: '',
  globalLoading: false,
  mainFullScreen: false,
  scrollerState: {
    scrollbar: false
  },
  breadcrumbs: {
    enable: false,
    title: '',
    backward: null
  }
}

const mutations = {
  setAppHeight(state, height) {
    state.appHeight = Math.max(0, Number(height) - Number(state.noticeHeight) || 0)
  },
  setNoticeHeight(state, height) {
    state.noticeHeight = Math.max(0, Number(height) || 0)
  },
  setNavStatus(state, { fold, stick }) {
    if (typeof fold !== 'undefined') {
      state.navFold = fold
    }
    if (typeof stick !== 'undefined') {
      state.navStick = stick
    }
  },
  setTitle(state, title) {
    state.title = title
  },
  setGlobalLoading(state, loading) {
    state.globalLoading = loading
  },
  setMainFullScreen(state, fullScreen) {
    state.mainFullScreen = fullScreen
  },
  setScrollerState(state, scrollerState) {
    state.scrollerState = {
      ...state.scrollerState,
      ...scrollerState
    }
  },
  setCustomBreadcrumbs(state, { enable, title, backward }) {
    state.breadcrumbs.enable = enable || false
    state.breadcrumbs.title = title || ''
    state.breadcrumbs.backward = backward || null
  }
}

const actions = {
  updateAppHeight({ commit }, height) {
    commit('setAppHeight', height)
  },
  updateNoticeHeight({ commit }, height) {
    commit('setNoticeHeight', height)
  },
  setNavStatus({ commit }, status) {
    commit('setNavStatus', status)
  }
}

const getters = {
  appHeight: (state) => state.appHeight,
  noticeHeight: (state) => state.noticeHeight,
  navStick: (state) => state.navStick,
  navFold: (state) => state.navFold,
  title: (state) => state.title,
  globalLoading: (state) => state.globalLoading,
  mainFullScreen: (state) => state.mainFullScreen,
  breadcrumbs: (state) => state.breadcrumbs
}

export default {
  namespaced: false,
  state,
  mutations,
  actions,
  getters
}
