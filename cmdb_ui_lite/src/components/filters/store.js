import Vue from 'vue'
import Utils from './utils'
import RouterQuery from '@/utils/router-query'
import QS from 'qs'
import userCustom from '@/api/user-custom'

const FilterStore = new Vue({
  data() {
    return {
      bk_biz_id: 0,
      modelIds: [],
      searchHandler: null,
      urlSync: false,
      suppressUrlWrite: false,
      modelPropertyMap: {},
      selected: [],
      condition: {},
      IP: Utils.getDefaultIP(),
      components: {},
      userBehavior: [],
      page: 1,
      pageSize: 20,
      // 用户级「条件筛选收藏」：数据落在服务端 user_custom 表（config_key='filter_collection'，
      // 按登录用户隔离），每条收藏 = { id, name, conditions }，conditions 即 bk_property_id -> {operator, value}，
      // 与 FilterStore.condition 完全一致。收藏与条件状态以 FilterStore 为单一数据源，自然同步。
      collections: [],
      activeCollection: null
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
    setUrlSync(flag) {
      this.urlSync = !!flag
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
    // ===== 条件筛选收藏（用户级，与条件状态以本 store 为单一数据源） =====
    /**
     * 从服务端 user_custom（config_key='filter_collection'）加载收藏列表
     */
    async loadCollections() {
      try {
        const cfg = await userCustom.searchUserCustom()
        this.collections = (cfg && Array.isArray(cfg.filter_collection)) ? cfg.filter_collection : []
      } catch (e) {
        console.error('[FilterStore] loadCollections failed', e)
        this.collections = []
      }
      return this.collections
    },
    /**
     * 在 modelPropertyMap 中按 bk_property_id 反查 property 对象（bk_property_id 全局唯一）
     */
    findPropertyInModelMap(bkPropertyId) {
      const map = this.modelPropertyMap || {}
      for (const modelId of Object.keys(map)) {
        const found = (map[modelId] || []).find(p => p.bk_property_id === bkPropertyId)
        if (found) return found
      }
      return null
    },
    /**
     * 应用收藏：把 collection.conditions 同步回 selected/condition（与条件状态同步），并触发搜索。
     * collection=null 时清空收藏激活态并重置筛选。
     */
    setActiveCollection(collection) {
      if (!collection) {
        this.activeCollection = null
        this.resetAll()
        return
      }
      try {
        const conditions = collection.conditions || {}
        const selected = []
        const condition = {}
        Object.keys(conditions).forEach(id => {
          const prop = this.findPropertyInModelMap(id)
          if (prop) {
            selected.push(prop)
            condition[id] = { operator: conditions[id].operator, value: conditions[id].value }
          }
        })
        // 先更新 selected（触发 watch -> initCondition 会保留已有 key），
        // 再于 nextTick 写入 condition 并触发搜索（与 FilterForm.handleSearch 一致）
        this.updateSelected(selected)
        this.condition = condition
        this.$nextTick(() => {
          this.condition = condition
          this.activeCollection = collection
          this.dispatchSearch()
        })
      } catch (e) {
        console.error('[FilterStore] setActiveCollection failed', e)
      }
    },
    /**
     * 从当前 selected/condition 序列化并保存为新收藏（收藏 = 当前条件）
     * @param {Object} payload
     * @param {string} payload.name 收藏名称
     * @param {Object} [payload.conditions] 可选，直接传入的 live 条件（bk_property_id -> {operator,value}）；
     *                                      不传时从 FilterStore.selected/condition 派生（兜底）。
     */
    async createCollection({ name, conditions: incomingConditions }) {
      let conditions = incomingConditions
      if (!conditions) {
        conditions = {}
        this.selected.forEach(property => {
          const id = property.bk_property_id
          const cond = this.condition[id]
          if (cond) {
            conditions[id] = { operator: cond.operator, value: cond.value }
          }
        })
      }
      const collection = { id: Date.now(), name: name || '未命名收藏', conditions }
      const collections = [collection, ...this.collections]
      await this.saveCollections(collections)
      this.collections = collections
      // 收藏即应用：把刚保存的条件同步回 selected/condition 并触发搜索，
      // 保证「收藏数据与条件状态同步」（与上游 createCollection 语义一致）
      this.setActiveCollection(collection)
      return collection
    },
    async removeCollection(collection) {
      const collections = this.collections.filter(c => c.id !== collection.id)
      await this.saveCollections(collections)
      this.collections = collections
      if (this.activeCollection && this.activeCollection.id === collection.id) {
        this.activeCollection = null
      }
    },
    async updateCollection({ id, name }) {
      const collections = this.collections.map(c => (c.id === id ? { ...c, name } : c))
      await this.saveCollections(collections)
      this.collections = collections
      if (this.activeCollection && this.activeCollection.id === id) {
        this.activeCollection = { ...this.activeCollection, name }
      }
    },
    async saveCollections(collections) {
      try {
        await userCustom.saveUsercustom({ filter_collection: collections })
      } catch (e) {
        console.error('[FilterStore] saveCollections failed', e)
        throw e
      }
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
      if (this.urlSync) {
        // URL 驱动：写入 URL 后由页面的 RouterQuery.watch('*') 触发列表刷新（与原版 bk-cmdb 一致）
        this.setQuery()
        return
      }
      if (this.searchHandler) {
        this.searchHandler(this.condition)
      }
    },
    findProperty(id, properties) {
      const list = properties || []
      return list.find(p => p.bk_property_id === id) || null
    },
    convertValue(value, operator, property) {
      if (!property) return value
      const type = property.bk_property_type
      let arr = Array.isArray(value) ? value.slice() : String(value).split(',')
      if (['int', 'float', 'double', 'long', 'foreignkey'].includes(type)) {
        arr = arr.map(v => parseInt(v, 10))
      } else if (type === 'bool') {
        arr = arr.map(v => v === true || v === 'true')
      }
      if (['$in', '$nin', '$range'].includes(operator)) return arr
      return arr[0]
    },
    /**
     * 将内存中的筛选条件序列化为 URL query
     * 与原版一致：filter = QS({ "id.operator": value })，ip = IP 对象，_t = 时间戳缓存破坏键
     */
    getQuery(condition) {
      const query = {}
      Object.keys(condition || {}).forEach((id) => {
        const { operator, value } = condition[id] || {}
        if (value === null || value === undefined) return
        const isEmpty = Array.isArray(value) ? value.length === 0 : String(value).length === 0
        if (isEmpty) return
        query[`${id}.${String(operator || '').replace('$', '')}`] = Array.isArray(value) ? value.join(',') : value
      })
      const ipObj = (this.IP && this.IP.text && this.IP.text.trim().length) ? this.IP : {}
      return {
        filter: QS.stringify(query, { encode: false }),
        ip: QS.stringify(ipObj, { encode: false }),
        _t: Date.now()
      }
    },
    /**
     * 将筛选条件写入 URL（router.replace，不污染历史）
     */
    setQuery() {
      if (!this.urlSync || this.suppressUrlWrite) return
      const allQuery = this.getQuery(this.condition)
      allQuery.page = 1
      RouterQuery.set(allQuery)
    },
    /**
     * 从 URL 的 filter 串还原筛选条件（页面刷新/前进后退后恢复）
     */
    setupPropertyQuery(properties) {
      const query = QS.parse(RouterQuery.get('filter') || '')
      const condition = {}
      const selected = []
      Object.keys(query).forEach((key) => {
        const idx = key.lastIndexOf('.')
        if (idx <= 0) return
        const id = key.slice(0, idx)
        const operator = `$${key.slice(idx + 1)}`
        const property = this.findProperty(id, properties) || this.findProperty(id, this.selected)
        const raw = query[key]
        const value = this.convertValue(raw, operator, property)
        if (property) selected.push(property)
        condition[id] = { operator, value }
      })
      this.selected = selected
      this.condition = condition
    },
    /**
     * 从 URL 的 ip 串还原 IP 筛选
     */
    setupIPQuery() {
      const query = QS.parse(RouterQuery.get('ip') || '')
      const { text = '', exact = 'false', inner = 'true', outer = 'true' } = query
      this.IP = {
        text: text ? String(text).replace(/,/g, '\n') : '',
        exact: String(exact) === 'true',
        inner: String(inner) === 'true',
        outer: String(outer) === 'true'
      }
    },
    /**
     * 从 URL 整体还原筛选条件（属性条件 + IP）
     */
    restoreFromUrl(properties) {
      this.setupPropertyQuery(properties)
      this.setupIPQuery()
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

export const setupFilterStore = async ({ bk_biz_id, modelIds, searchHandler, modelPropertyMap, urlSync }) => {
  FilterStore.setBizId(bk_biz_id)
  FilterStore.setModelIds(modelIds)
  FilterStore.setSearchHandler(searchHandler)
  FilterStore.setUrlSync(urlSync)

  if (modelPropertyMap) {
    FilterStore.setModelPropertyMap(modelPropertyMap)
  }

  // 初始化期不写 URL，避免把进入页面时 URL 中已有的筛选条件清掉
  // （随后由页面的 restoreFromUrl 从 URL 回放到 store）
  FilterStore.suppressUrlWrite = true
  FilterStore.resetAll()
  FilterStore.suppressUrlWrite = false
}

export default FilterStore