import Vue from 'vue'
import Vuex from 'vuex'
import objectModelClassify from './modules/objectModelClassify.js'

Vue.use(Vuex)

export default new Vuex.Store({
  modules: {
    objectModelClassify
  },
  state: {
    userCustom: {
      customTableColumns: {}
    },
    currentInstance: {
      name: '',
      objId: '',
      instId: ''
    }
  },
  mutations: {
    SET_USERCUSTOM(state, payload) {
      state.userCustom.customTableColumns = {
        ...state.userCustom.customTableColumns,
        ...payload
      }
    },
    LOAD_ALL_USERCUSTOM(state, usercustom) {
      if (usercustom && typeof usercustom === 'object') {
        Object.keys(usercustom).forEach(key => {
          if (key.includes('custom_table_columns')) {
            Vue.set(state.userCustom.customTableColumns, key, usercustom[key])
          }
        })
      }
    },
    SET_CURRENT_INSTANCE(state, payload) {
      state.currentInstance = {
        ...state.currentInstance,
        ...payload
      }
    }
  },
  actions: {
    saveUsercustom({ commit }, payload) {
      const key = Object.keys(payload)[0]
      const value = payload[key]
      commit('SET_USERCUSTOM', payload)
      console.log('[UserCustom] 保存自定义配置:', key, value)
    },
    loadAllUserCustom({ commit }, usercustom) {
      commit('LOAD_ALL_USERCUSTOM', usercustom)
      console.log('[UserCustom] 批量加载自定义配置:', Object.keys(usercustom))
    },
    setCurrentInstance({ commit }, instanceData) {
      commit('SET_CURRENT_INSTANCE', instanceData)
      console.log('[Instance] 设置当前实例:', instanceData)
    }
  },
  getters: {
    getCustomColumns: (state) => (objId) => {
      const key = `${objId}_custom_table_columns`
      return state.userCustom.customTableColumns[key] || []
    }
  }
})
