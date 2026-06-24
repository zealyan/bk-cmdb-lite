import Vue from 'vue'
import userCustomAPI from '@/api/user-custom'
import { MENU_RESOURCE_COLLECTION } from '@/dictionary/menu-symbol'

const state = {
  usercustom: {}
}

const getters = {
  usercustom: state => state.usercustom,
  getCustomData: state => (key, defaultData = null) => {
    if (Object.prototype.hasOwnProperty.call(state.usercustom, key)) {
      return state.usercustom[key]
    }
    return defaultData
  },
  resourceCollection: (state, getters, rootState, rootGetters) => {
    const collection = state.usercustom[MENU_RESOURCE_COLLECTION] || []
    const models = rootGetters['objectModelClassify/models']
    return collection.filter(modelId => models.some(model => model.bk_obj_id === modelId))
  }
}

const actions = {
  async saveUsercustom({ commit, state }, usercustom = {}) {
    try {
      await userCustomAPI.saveUsercustom(usercustom)
      commit('setUsercustom', usercustom)
      return state.usercustom
    } catch (error) {
      console.error('[userCustom] 保存用户配置失败:', error)
      throw error
    }
  },
  async searchUsercustom({ commit }) {
    try {
      const usercustom = await userCustomAPI.searchUserCustom()
      commit('setUsercustom', usercustom)
      return usercustom
    } catch (error) {
      console.error('[userCustom] 获取用户配置失败:', error)
      return {}
    }
  }
}

const mutations = {
  setUsercustom(state, usercustom = {}) {
    for (const key in usercustom) {
      if (Object.prototype.hasOwnProperty.call(usercustom, key)) {
        Vue.set(state.usercustom, key, usercustom[key])
      }
    }
  }
}

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations
}
