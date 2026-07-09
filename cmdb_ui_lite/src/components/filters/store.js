class FilterStore {
  constructor () {
    this.bk_biz_id = 0
    this.modelIds = []
    this.searchHandler = null
    this.modelPropertyMap = {}
    this.selected = []
    this.condition = {}
    this.IP = {}
    this.components = {}
    this.userBehavior = []
    this.page = 1
    this.pageSize = 20
  }

  setBizId (bizId) {
    this.bk_biz_id = bizId
  }

  setModelIds (modelIds) {
    this.modelIds = modelIds
  }

  setSearchHandler (handler) {
    this.searchHandler = handler
  }

  setModelPropertyMap (map) {
    this.modelPropertyMap = map
  }

  updateSelected (selected) {
    this.selected = selected
  }

  updateCondition (condition) {
    this.condition = { ...this.condition, ...condition }
  }

  setCondition (data) {
    if (data.condition) {
      this.condition = data.condition
    }
    if (data.IP) {
      this.IP = data.IP
    }
    this.dispatchSearch()
  }

  updateIP (IP) {
    this.IP = IP
  }

  updateUserBehavior (selected) {
    const behaviors = [...this.userBehavior]
    selected.forEach(item => {
      const index = behaviors.findIndex(behavior => behavior.id === item.id)
      if (index > -1) {
        behaviors.splice(index, 1)
      }
      behaviors.unshift(item)
    })
    this.userBehavior = behaviors.slice(0, 10)
  }

  resetPage (keepPage) {
    if (!keepPage) {
      this.page = 1
    }
  }

  resetAll () {
    this.selected = []
    this.condition = {}
    this.IP = {}
    this.page = 1
    this.dispatchSearch()
  }

  hasCondition () {
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
  }

  dispatchSearch () {
    if (this.searchHandler) {
      this.searchHandler(this.condition)
    }
  }

  setComponent (name, component) {
    this.components[name] = component
  }

  getComponent (name) {
    return this.components[name]
  }

  createOrUpdateCondition (fields, options = {}) {
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
  }
}

const filterStore = new FilterStore()

export const setupFilterStore = async ({ bk_biz_id, modelIds, searchHandler, modelPropertyMap }) => {
  filterStore.setBizId(bk_biz_id)
  filterStore.setModelIds(modelIds)
  filterStore.setSearchHandler(searchHandler)

  if (modelPropertyMap) {
    filterStore.setModelPropertyMap(modelPropertyMap)
  }

  filterStore.resetAll()
}

export default filterStore