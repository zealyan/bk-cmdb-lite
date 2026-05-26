import Vue from 'vue'
import { modelAPI } from '@/api/client'

const state = {
  classifications: [],
  models: [],
  loading: false,
  error: null
}

const getters = {
  classifications: state => state.classifications,
  models: state => state.models,
  getModelById: (state) => (objId) => {
    return state.models.find(model => model.bk_obj_id === objId)
  },
  getModelsByClassification: (state) => (classificationId) => {
    return state.models.filter(model => model.bk_classification_id === classificationId)
  },
  getClassificationById: (state) => (classificationId) => {
    return state.classifications.find(cls => cls.bk_classification_id === classificationId)
  }
}

const mutations = {
  SET_CLASSIFICATIONS(state, classifications) {
    state.classifications = classifications
  },
  SET_MODELS(state, models) {
    state.models = models
  },
  SET_LOADING(state, loading) {
    state.loading = loading
  },
  SET_ERROR(state, error) {
    state.error = error
  },
  SET_CLASSIFICATIONS_WITH_OBJECTS(state, data) {
    state.classifications = data
    const allModels = []
    data.forEach(cls => {
      if (cls.bk_objects && Array.isArray(cls.bk_objects)) {
        cls.bk_objects.forEach(model => {
          allModels.push({
            ...model,
            bk_classification_name: cls.bk_classification_name,
            bk_classification_id: cls.bk_classification_id
          })
        })
      }
    })
    state.models = allModels
  }
}

const actions = {
  async searchClassificationsObjects({ commit }) {
    commit('SET_LOADING', true)
    commit('SET_ERROR', null)
    
    try {
      console.log('[ObjectModelClassify] 调用 searchClassificationsObjects API...')
      const response = await modelAPI.searchClassificationsObjects()
      console.log('[ObjectModelClassify] API 返回数据类型:', typeof response)
      console.log('[ObjectModelClassify] API 返回数据:', JSON.stringify(response))
      
      const data = Array.isArray(response) ? response : (response.data || response.result || [])
      console.log('[ObjectModelClassify] 处理后的数据:', data)
      
      commit('SET_CLASSIFICATIONS_WITH_OBJECTS', data)
      return data
    } catch (error) {
      console.error('[ObjectModelClassify] API 调用失败:', error)
      commit('SET_ERROR', error.message || '获取模型分类失败')
      throw error
    } finally {
      commit('SET_LOADING', false)
    }
  },
  
  async loadModels({ commit }) {
    try {
      const data = await modelAPI.listModels()
      commit('SET_MODELS', data.models || [])
      return data.models
    } catch (error) {
      console.error('[ObjectModelClassify] 加载模型列表失败:', error)
      throw error
    }
  },
  
  async loadClassifications({ commit }) {
    try {
      const data = await modelAPI.listClassifications()
      commit('SET_CLASSIFICATIONS', data.classifications || [])
      return data.classifications
    } catch (error) {
      console.error('[ObjectModelClassify] 加载分类列表失败:', error)
      throw error
    }
  }
}

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions
}
