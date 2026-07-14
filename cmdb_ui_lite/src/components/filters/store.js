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
      handler(newVal, oldVal) {
        // 只在 selected 真正变化时才重建 condition
        // 避免在 handleSearch 中 updateSelected 后的 watch 覆盖 setCondition 的值
        if (!oldVal || !newVal || newVal.length !== oldVal.length ||
            newVal.some((item, i) => item.bk_property_id !== (oldVal[i] && oldVal[i].bk_property_id))) {
          this.initCondition()
        }
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
      console.log('[FilterStore] updateSelected:', selected.map(p => p.bk_property_id))
      this.selected = selected
    },
    updateCondition(condition) {
      this.condition = { ...this.condition, ...condition }
    },
    setCondition(data) {
      console.log('[FilterStore] setCondition → data:', JSON.stringify(data))
      if (data.condition) {
        this.condition = data.condition
      }
      if (data.IP) {
        this.IP = data.IP
      }
      console.log('[FilterStore] setCondition → this.condition:', JSON.stringify(this.condition))
      console.log('[FilterStore] setCondition → this.selected:', this.selected.map(p => p.bk_property_id))
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
    removeSelected(property) {
      const index = this.selected.findIndex(target => target.bk_property_id === property.bk_property_id)
      if (index > -1) {
        this.selected.splice(index, 1)
      }
    },
    resetValue(property, silent = false) {
      const properties = Array.isArray(property) ? property : [property]
      properties.forEach((target) => {
        const id = target.bk_property_id
        if (this.condition[id]) {
          const { operator } = this.condition[id]
          const value = Utils.getOperatorSideEffect(target, operator, '')
          this.$set(this.condition, id, { operator, value })
        }
      })
      this.updateUserBehavior(properties)
      if (!silent) {
        this.dispatchSearch()
      }
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
      console.log('[FilterStore] initCondition → current condition:', JSON.stringify(this.condition))
      console.log('[FilterStore] initCondition → selected keys:', this.selected.map(p => p.bk_property_id))
      const newCondition = {}
      this.selected.forEach((property) => {
        const id = property.bk_property_id
        if (Object.prototype.hasOwnProperty.call(this.condition, id)) {
          // 保留已有值，不被覆盖
          newCondition[id] = this.condition[id]
        } else {
          // 新属性使用默认值
          newCondition[id] = Utils.getDefaultData(property)
        }
      })
      // 只在 key 集合变化时才替换，避免覆盖已有值
      const oldKeys = Object.keys(this.condition).sort().join(',')
      const newKeys = Object.keys(newCondition).sort().join(',')
      console.log('[FilterStore] initCondition → oldKeys:', oldKeys, 'newKeys:', newKeys)
      if (oldKeys !== newKeys) {
        this.condition = newCondition
        console.log('[FilterStore] initCondition → REPLACED condition:', JSON.stringify(this.condition))
      } else {
        console.log('[FilterStore] initCondition → NO CHANGE (keys match)')
      }
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