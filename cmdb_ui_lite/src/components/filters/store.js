import Vue from 'vue'
import Utils from './utils'

const FilterStore = new Vue({
  data() {
    return {
      bk_biz_id: 0,
      modelIds: [],
      searchHandler: null,
      modelPropertyMap: {},
      selected: [],
      condition: {},
      IP: Utils.getDefaultIP(),
      components: {},
      userBehavior: [],
      page: 1,
      pageSize: 20
    }
  },
  watch: {
    selected: {
      handler() {
        this.initCondition()
      }
    }
  },
  methods: {
    setBizId(bizId) {
      this.bk_biz_id = bizId
    },
    setModelIds(modelIds) {
      this.modelIds = modelIds
    },
    setSearchHandler(handler) {
      this.searchHandler = handler
    },
    setModelPropertyMap(map) {
      this.modelPropertyMap = map
    },
    updateSelected(selected) {
      this.selected = selected
    },
    updateCondition(condition) {
      this.condition = { ...this.condition, ...condition }
    },
    setCondition(data) {
      if (data.condition) {
        this.condition = data.condition
      }
      if (data.IP) {
        this.IP = data.IP
      }
      this.dispatchSearch()
    },
    updateIP(IP) {
      this.IP = IP
    },
    updateUserBehavior(selected) {
      const behaviors = [...this.userBehavior]
      selected.forEach(item => {
        const index = behaviors.findIndex(behavior => behavior.bk_property_id === item.bk_property_id)
        if (index > -1) {
          behaviors.splice(index, 1)
        }
        behaviors.unshift(item)
      })
      this.userBehavior = behaviors.slice(0, 10)
    },
    resetPage(keepPage) {
      if (!keepPage) {
        this.page = 1
      }
    },
    resetAll() {
      this.selected = []
      this.condition = {}
      this.IP = Utils.getDefaultIP()
      this.page = 1
      this.dispatchSearch()
    },
    hasCondition() {
      const hasIP = Object.keys(this.IP).some(key => {
        const value = this.IP[key]
        if (value === null || value === undefined || value === '') {
          return false
        }
        if (Array.isArray(value)) {
          return value.length > 0
        }
        return true
      })
      if (hasIP) return true

      const hasCondition = Object.keys(this.condition).some(key => {
        const cond = this.condition[key]
        if (!cond) return false
        const value = cond.value
        if (value === null || value === undefined || value === '') {
          return false
        }
        if (Array.isArray(value)) {
          return value.length > 0
        }
        return true
      })
      return hasCondition
    },
    dispatchSearch() {
      if (this.searchHandler) {
        this.searchHandler(this.condition)
      }
    },
    setComponent(name, component) {
      this.components[name] = component
    },
    getComponent(name) {
      return this.components[name]
    },
    createOrUpdateCondition(fields, options = {}) {
      const { createOnly = false, useDefaultData = false } = options
      let updated = false

      fields.forEach(item => {
        const { field, model } = item
        const id = `${model}_${field}`

        if (createOnly && this.condition[id]) {
          return
        }

        if (!this.condition[id]) {
          this.condition[id] = {
            operator: '',
            value: useDefaultData ? '' : null
          }
          updated = true
        }
      })

      if (updated) {
        this.dispatchSearch()
      }
    },
    initCondition() {
      const newCondition = {}
      this.selected.forEach((property) => {
        const id = property.bk_property_id
        if (Object.prototype.hasOwnProperty.call(this.condition, id)) {
          newCondition[id] = this.condition[id]
        } else {
          newCondition[id] = Utils.getDefaultData(property)
        }
      })
      this.condition = newCondition
    }
  }
})

export const setupFilterStore = async ({ bk_biz_id, modelIds, searchHandler, modelPropertyMap }) => {
  FilterStore.setBizId(bk_biz_id)
  FilterStore.setModelIds(modelIds)
  FilterStore.setSearchHandler(searchHandler)

  if (modelPropertyMap) {
    FilterStore.setModelPropertyMap(modelPropertyMap)
  }

  FilterStore.resetAll()
}

export default FilterStore