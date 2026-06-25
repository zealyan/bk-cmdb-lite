<template>
  <bk-sideslider
    transfer
    :is-show.sync="isShow"
    :title="title"
    :width="sidesliderWidth"
    :quick-close="true"
    @hidden="handleHidden"
    class="general-model-filter-sideslider">
    <div class="filter-content" slot="content">
      <div class="filter-header">
        <div class="filter-operate">
          <condition-picker
            :properties="properties"
            :selected="filterItems.map(item => item.property)"
            :disabled="!showAddButton"
            :handler="handleAddConditions"
          ></condition-picker>
          <bk-button
            v-if="hasCondition"
            class="clear-btn"
            :text="true"
            theme="primary"
            @click="handleClearAll">
            清空条件
          </bk-button>
        </div>
      </div>

      <div class="filter-condition-list" ref="conditionList">
        <div
          v-for="(item, index) in filterItems"
          :key="item.id"
          class="filter-item no-expand"
          :class="{ 'is-last': index === filterItems.length - 1 && !showAddButton }">
          <div class="item-header">
            <label class="item-label">
              {{ item.property.bk_property_name }}
              <span class="item-label-suffix">({{ item.property.bk_obj_name || item.property.bk_obj_id }})</span>
            </label>
            <i class="item-remove bk-icon icon-close" @click="handleRemoveItem(index)"></i>
          </div>
          <div class="item-content-wrapper">
            <bk-select
              v-if="!withoutOperator.includes(item.property.bk_property_type)"
              v-model="item.operator"
              :clearable="false"
              size="small"
              class="item-operator"
              @selected="handleOperatorChange(item)">
              <bk-option
                v-for="op in getOperators(item.property)"
                :key="op.id"
                :id="op.id"
                :name="op.name"
                :title="op.desc">
              </bk-option>
            </bk-select>
            <div class="item-value" :class="{ 'is-full': withoutOperator.includes(item.property.bk_property_type), 'r0': ['cmdb-search-enum', 'cmdb-search-enummulti', 'cmdb-search-list', 'cmdb-search-date', 'cmdb-search-time', 'cmdb-search-bool'].includes(getComponentType(item)) }">
              <component
                :is="getComponentType(item)"
                v-if="['cmdb-search-enum', 'cmdb-search-enummulti', 'cmdb-search-list', 'cmdb-search-bool'].includes(getComponentType(item))"
                v-model="item.valueText"
                :options="getSelectOptions(item.property)"
                :property="item.property"
                :placeholder="getPlaceholder(item)"
                size="small">
              </component>
              <component
                :is="getComponentType(item)"
                v-else-if="['cmdb-search-date', 'cmdb-search-time'].includes(getComponentType(item))"
                v-model="item.valueText"
                :property="item.property"
                :placeholder="getPlaceholder(item)"
                size="small">
              </component>
              <template v-else-if="getComponentType(item) === 'input'">
                <bk-input
                  v-if="isRangeOperator(item.operator)"
                  v-model="item.valueRange"
                  type="textarea"
                  :placeholder="getRangePlaceholder(item)"
                  :rows="1"
                  size="small"
                  @enter="handleSearch">
                </bk-input>
                <bk-input
                  v-else-if="isInOperator(item.operator)"
                  v-model="item.valueText"
                  type="textarea"
                  :placeholder="getInPlaceholder(item)"
                  :rows="1"
                  size="small"
                  @enter="handleSearch">
                </bk-input>
                <bk-input
                  v-else
                  v-model="item.valueText"
                  :placeholder="getPlaceholder(item)"
                  size="small"
                  @enter="handleSearch">
                </bk-input>
              </template>
              <bk-input
                v-else-if="getComponentType(item) === 'textarea'"
                v-model="item.valueText"
                type="textarea"
                :placeholder="getPlaceholder(item)"
                :rows="2"
                size="small"
                @enter="handleSearch">
              </bk-input>
            </div>
          </div>
        </div>
      </div>

      <div class="filter-footer">
        <bk-button
          theme="primary"
          :disabled="!hasCondition"
          @click="handleSearch">
          查询
        </bk-button>
        <bk-button @click="handleReset">清空</bk-button>
      </div>
    </div>
  </bk-sideslider>
</template>

<script>
import { QUERY_OPERATOR } from '@/utils/query-operator'
import ConditionPicker from '../condition-picker/index.vue'
import EnumSearch from '../search/enum.vue'
import EnumMultiSearch from '../search/enummulti.vue'
import ListSearch from '../search/list.vue'
import DateSearch from '../search/date.vue'
import TimeSearch from '../search/time.vue'
import BoolSearch from '../search/bool.vue'
import { transformGeneralModelCondition, getOperatorSideEffect } from './utils'
import { setSearchQueryByCondition, buildSearchParams } from '@/utils/query-builder'

const { EQ, NE, IN, NIN, GT, LT, GTE, LTE, RANGE, LIKE } = QUERY_OPERATOR

export default {
  name: 'GeneralModelFilter',
  components: {
    ConditionPicker,
    'cmdb-search-enum': EnumSearch,
    'cmdb-search-enummulti': EnumMultiSearch,
    'cmdb-search-list': ListSearch,
    'cmdb-search-date': DateSearch,
    'cmdb-search-time': TimeSearch,
    'cmdb-search-bool': BoolSearch
  },
  props: {
    show: {
      type: Boolean,
      default: false
    },
    properties: {
      type: Array,
      default: () => []
    },
    loadedData: {
      type: Array,
      default: () => []
    },
    conditionMap: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      isShow: false,
      filterItems: [],
      nextItemId: 1,
      withoutOperator: ['bool', 'date', 'time'],
      operatorsMap: {
        float: [EQ, NE, GT, LT, GTE, LTE, RANGE, IN, LIKE],
        int: [EQ, NE, GT, LT, GTE, LTE, RANGE, IN, LIKE],
        singlechar: [IN, NIN, LIKE],
        longchar: [IN, NIN, LIKE],
        enum: [IN, NIN, EQ],
        list: [IN, NIN],
        enummulti: [IN, NIN],
        date: [GTE, LTE, RANGE],
        time: [GTE, LTE, RANGE],
        objuser: [IN, NIN],
        organization: [IN, NIN],
        timezone: [IN, NIN],
        foreignkey: [IN, NIN],
        array: [IN, NIN, LIKE],
        object: [IN, NIN, LIKE],
        bool: [EQ, NE]
      },
      operatorSymbolMap: {
        [EQ]: { symbol: '=', desc: '等于' },
        [NE]: { symbol: '≠', desc: '不等于' },
        [IN]: { symbol: 'in', desc: '包含在' },
        [NIN]: { symbol: 'not in', desc: '不包含在' },
        [GT]: { symbol: '>', desc: '大于' },
        [LT]: { symbol: '<', desc: '小于' },
        [GTE]: { symbol: '≥', desc: '大于等于' },
        [LTE]: { symbol: '≤', desc: '小于等于' },
        [RANGE]: { symbol: '≤ ≥', desc: '范围' },
        [LIKE]: { symbol: '~', desc: '模糊匹配' }
      }
    }
  },
  computed: {
    title() {
      return '高级筛选'
    },
    sidesliderWidth() {
      const screenWidth = window.innerWidth
      if (screenWidth >= 768) {
        return 400
      } else if (screenWidth >= 480) {
        return Math.floor(screenWidth * 0.85)
      }
      return Math.floor(screenWidth * 0.95)
    },
    hasCondition() {
      return this.filterItems.some(item => {
        const value = this.getItemValue(item)
        return value !== null && value !== undefined && String(value).length > 0
      })
    },
    showAddButton() {
      // 与原项目保持一致: 排除 bk_isapi=true 的系统字段和 id 字段
      const availableProperties = this.properties.filter(p => {
        if (p.bk_property_id === 'id' || p.bk_isapi) return false
        const usedIds = this.filterItems.map(item => item.property.bk_property_id)
        return !usedIds.includes(p.bk_property_id)
      })
      return availableProperties.length > 0
    }
  },
  watch: {
    show: {
      immediate: true,
      handler(val) {
        this.isShow = val
        if (val) {
          console.log('[GeneralModelFilter] 抽屉打开, conditionMap:', JSON.stringify(this.conditionMap))
          if (this.conditionMap && Object.keys(this.conditionMap).length > 0) {
            console.log('[GeneralModelFilter] 开始恢复条件，properties 数量:', this.properties.length)
            // 如果有条件，从 conditionMap 恢复
            this.restoreItemsFromConditionMap()
            console.log('[GeneralModelFilter] 恢复后 filterItems:', JSON.stringify(this.filterItems.map(item => ({
              id: item.id, propertyId: item.property.bk_property_id, operator: item.operator, valueText: item.valueText
            }))))
          } else if (this.filterItems.length === 0) {
            // 没有条件时，初始化默认项
            console.log('[GeneralModelFilter] 初始化默认项')
            this.initDefaultItem()
          }
        }
      }
    },
    isShow(val) {
      this.$emit('update:show', val)
    },
    // 监听 conditionMap 变化，当从详情页返回或删除标签时，确保同步更新条件
    conditionMap: {
      deep: true,
      handler(val) {
        console.log('[GeneralModelFilter] conditionMap 变化:', val)
        if (!val || Object.keys(val).length === 0) {
          // 条件为空时，清空所有条件
          console.log('[GeneralModelFilter] conditionMap 为空，清空条件')
          this.clearAllConditions()
        } else {
          // 无论抽屉是否打开，都更新条件（因为抽屉可能在条件变化后打开）
          console.log('[GeneralModelFilter] 恢复/更新条件')
          this.restoreItemsFromConditionMap()
        }
      }
    }
  },
  methods: {
    restoreItemsFromConditionMap() {
      if (!this.conditionMap || Object.keys(this.conditionMap).length === 0) {
        return
      }

      this.filterItems = []
      const conditionKeys = Object.keys(this.conditionMap)
      
      conditionKeys.forEach(fieldId => {
        const property = this.properties.find(p => p.bk_property_id === fieldId)
        if (!property) {
          console.warn('[GeneralModelFilter] 找不到属性:', fieldId, '当前属性:', this.properties.map(p => p.bk_property_id))
          return
        }
        
        const condition = this.conditionMap[fieldId]
        const { operator, value } = condition
        
        // 添加项
        const propType = property.bk_property_type
        const isEnum = propType === 'enum'
        const isEnumMulti = propType === 'enummulti'
        const isBool = propType === 'bool'
        const isList = propType === 'list'
        const isEnumOrList = isEnum || isEnumMulti || isList || isBool
        const isDateTime = ['date', 'time'].includes(propType)
        
        let valueText = ''
        let valueRange = ''
        
        if (isDateTime) {
          // 对于日期时间类型，cmdb-search-date 和 cmdb-search-time 组件绑定的是 valueText
          valueText = Array.isArray(value) ? [...value] : (value ? [value] : [])
        } else if (isEnumOrList) {
          // 枚举、布尔、列表类型使用 $in 操作符，值为数组
          const isInOp = this.isInOperator(operator)
          if (isInOp && typeof value === 'string') {
            valueText = value.split(',').map(v => v.trim()).filter(v => v)
          } else {
            valueText = Array.isArray(value) ? [...value] : (value ? [value] : [])
          }
        } else if (this.isRangeOperator(operator)) {
          valueRange = Array.isArray(value) ? value.join('\n') : value
        } else if (this.isInOperator(operator)) {
          // in 操作符的值可能是数组，需要处理
          if (Array.isArray(value)) {
            valueText = value.join('\n')
          } else {
            valueText = String(value)
          }
        } else {
          valueText = Array.isArray(value) ? value.join(',') : value
        }
        
        this.filterItems.push({
          id: this.nextItemId++,
          property,
          operator,
          valueText,
          valueRange
        })
      })
      
      console.log('[GeneralModelFilter] 恢复完成, filterItems:', this.filterItems.map(item => ({
        property: item.property.bk_property_id,
        operator: item.operator,
        valueText: item.valueText,
        valueRange: item.valueRange,
        type: item.property.bk_property_type
      })))
    },
    getItemValue(item) {
      const propType = item.property.bk_property_type
      const isEnum = propType === 'enum'
      const isEnumMulti = propType === 'enummulti'
      const isList = propType === 'list'
      const isBool = propType === 'bool'
      const isEnumOrList = isEnum || isEnumMulti || isList
      const isDateTime = ['date', 'time'].includes(propType)
      
      if (this.isRangeOperator(item.operator)) {
        // 范围操作符返回 valueRange
        return item.valueRange || ''
      }
      
      if (isEnumOrList || isDateTime) {
        return item.valueText || []
      }
      
      if (isBool) {
        return item.valueText || ''
      }
      
      if (this.isInOperator(item.operator)) {
        return item.valueText || ''
      }
      
      return item.valueText || ''
    },
    initDefaultItem() {
      // 与原项目保持一致: 排除 bk_isapi=true 的系统字段和 id 字段
      if (this.properties.length > 0) {
        const sortedProperties = [...this.properties]
          .filter(p => p.bk_property_index >= 0 && p.bk_property_id !== 'id' && !p.bk_isapi)
          .sort((a, b) => a.bk_property_index - b.bk_property_index)
        
        if (sortedProperties.length > 0) {
          this.addItem(sortedProperties[0])
        }
      }
    },
    getOperators(property) {
      const type = property.bk_property_type
      const operators = this.operatorsMap[type] || [EQ]
      return operators.map(op => ({
        id: op,
        name: this.operatorSymbolMap[op]?.symbol || op,
        desc: this.operatorSymbolMap[op]?.desc || op
      }))
    },
    isRangeOperator(operator) {
      return operator === RANGE
    },
    isInOperator(operator) {
      return [IN, NIN].includes(operator)
    },
    getComponentType(item) {
      const { property, operator } = item
      const type = property.bk_property_type

      if (type === 'enum') {
        return 'cmdb-search-enum'
      }

      if (type === 'enummulti') {
        return 'cmdb-search-enummulti'
      }

      if (type === 'list') {
        return 'cmdb-search-list'
      }

      if (type === 'date') {
        return 'cmdb-search-date'
      }

      if (type === 'time') {
        return 'cmdb-search-time'
      }

      if (this.isInOperator(operator)) {
        return 'input'
      }

      if (type === 'bool') {
        return 'cmdb-search-bool'
      }

      const inputTypes = ['int', 'float', 'singlechar', 'longchar', 'objuser', 'organization', 'timezone', 'foreignkey', 'array', 'object', 'map', 'table']
      const textareaTypes = ['text']

      if (textareaTypes.includes(type)) {
        return 'textarea'
      }
      if (inputTypes.includes(type)) {
        return 'input'
      }

      return 'input'
    },
    getSelectOptions(property) {
      if (property.bk_property_type === 'bool') {
        return [
          { id: 'true', name: 'true' },
          { id: 'false', name: 'false' }
        ]
      }
      const option = property.option
      if (option && Array.isArray(option)) {
        if (option.length > 0 && option[0] && typeof option[0] === 'object' && option[0].id !== undefined) {
          return option.map(opt => ({
            id: opt.id,
            name: opt.name
          }))
        } else {
          return option.map(opt => ({
            id: opt,
            name: opt
          }))
        }
      }
      return []
    },
    getUniqueValuesFromData(fieldId) {
      const uniqueValues = new Set()
      const dataList = this.loadedData || []

      dataList.forEach(row => {
        const value = row[fieldId]
        if (value !== null && value !== undefined && value !== '') {
          uniqueValues.add(String(value))
        }
      })

      return Array.from(uniqueValues)
        .sort((a, b) => a.localeCompare(b, 'zh-CN'))
        .map(value => ({ id: value, name: value }))
    },
    getPlaceholder(item) {
      const name = item.property.bk_property_name
      const propertyType = item.property.bk_property_type
      const selectTypes = ['list', 'enum', 'timezone', 'organization', 'date', 'time', 'bool']
      if (selectTypes.includes(propertyType)) {
        return `请选择${name}`
      }
      return `请输入${name}`
    },
    getInPlaceholder(item) {
      const name = item.property.bk_property_name
      return `请输入${name}，多个值用换行分隔`
    },
    getRangePlaceholder(item) {
      const name = item.property.bk_property_name
      return `请输入${name}范围\n格式：最小值, 最大值\n或每行一个值`
    },
    addItem(property) {
      const defaultOperator = this.getDefaultOperator(property)
      const operators = this.getOperators(property)
      const operator = operators.length > 0 ? operators.find(op => op.id === defaultOperator)?.id || operators[0].id : defaultOperator

      const isEnum = property.bk_property_type === 'enum'
      const isEnumMulti = property.bk_property_type === 'enummulti'
      const isList = property.bk_property_type === 'list'
      const isBool = property.bk_property_type === 'bool'
      const isEnumOrList = isEnum || isEnumMulti || isList
      const isDateTime = ['date', 'time'].includes(property.bk_property_type)
      this.filterItems.push({
        id: this.nextItemId++,
        property,
        operator,
        valueText: isEnumOrList || isDateTime ? [] : (isBool ? '' : ''),
        valueRange: ''
      })
    },
    getDefaultOperator(property) {
      const type = property.bk_property_type
      const defaultMap = {
        singlechar: IN,
        longchar: IN,
        int: EQ,
        float: EQ,
        enum: IN,
        enummulti: IN,
        list: IN,
        bool: EQ,
        date: RANGE,
        time: RANGE,
        objuser: IN,
        organization: IN,
        timezone: IN,
        foreignkey: IN,
        array: IN,
        object: IN,
        map: EQ
      }

      return defaultMap[type] || EQ
    },
    handleAddConditions(properties) {
      properties.forEach(property => {
        if (!this.filterItems.some(item => item.property.bk_property_id === property.bk_property_id)) {
          this.addItem(property)
        }
      })
    },
    handleRemoveItem(index) {
      this.filterItems.splice(index, 1)
      if (this.filterItems.length === 0) {
        this.initDefaultItem()
      }
    },
    handleClearAll() {
      this.filterItems = []
      this.initDefaultItem()
    },
    handleOperatorChange(item) {
      const isEnum = item.property.bk_property_type === 'enum'
      const isEnumMulti = item.property.bk_property_type === 'enummulti'
      const isList = item.property.bk_property_type === 'list'
      const isBool = item.property.bk_property_type === 'bool'
      const isEnumOrList = isEnum || isEnumMulti || isList
      const isDateTime = ['date', 'time'].includes(item.property.bk_property_type)
      item.valueText = isEnumOrList || isDateTime ? [] : ''
      item.valueRange = ''
    },
    handleSearch() {
      const conditionMap = {}

      this.filterItems.forEach(item => {
        const value = this.getItemValue(item)
        const propType = item.property.bk_property_type
        const isEnum = propType === 'enum'
        const isEnumMulti = propType === 'enummulti'
        const isList = propType === 'list'
        const isBool = propType === 'bool'
        const isEnumOrList = isEnum || isEnumMulti || isList
        const isDateTime = ['date', 'time'].includes(propType)

        if (isEnumOrList || isDateTime) {
          if (Array.isArray(value) && value.length > 0) {
            conditionMap[item.property.bk_property_id] = {
              operator: item.operator,
              value
            }
          }
        } else if (isBool) {
          // bool 类型：值是 'true' 或 'false'（单个字符串）
          if (value === 'true' || value === 'false') {
            conditionMap[item.property.bk_property_id] = {
              operator: item.operator,
              value
            }
          }
        } else if (value !== null && value !== undefined && String(value).trim().length > 0) {
          let processedValue = value

          if (this.isInOperator(item.operator)) {
            processedValue = String(value).split(/[\n,，]/).map(v => v.trim()).filter(v => v.length > 0)
          } else if (this.isRangeOperator(item.operator)) {
            processedValue = String(value).split(/[\n,，]/).map(v => v.trim()).filter(v => v.length > 0)
          }

          conditionMap[item.property.bk_property_id] = {
            operator: item.operator,
            value: processedValue
          }
        }
      })

      const transformedCondition = transformGeneralModelCondition(conditionMap, this.properties)
      const searchParams = buildSearchParams(conditionMap, this.properties, {
        page: 1,
        pageSize: 20,
        sort: '-id'
      })

      setSearchQueryByCondition(conditionMap, this.properties)

      this.$emit('search', {
        conditionMap,
        transformedCondition,
        searchParams,
        rawConditions: Object.keys(conditionMap).map(id => ({
          field: id,
          ...conditionMap[id]
        }))
      })

      this.isShow = false
    },
    handleReset() {
      this.filterItems.forEach(item => {
        const value = getOperatorSideEffect(item.property, item.operator, [])
        item.value = value
      })
      this.$emit('reset')
    },
    handleHidden() {
      this.isShow = false
    },
    clearAllConditions() {
      console.log('[GeneralModelFilter] clearAllConditions 被调用')
      this.filterItems = []
      this.initDefaultItem()
    },
    removeConditionByPropertyId(propertyId) {
      console.log('[GeneralModelFilter] removeConditionByPropertyId:', propertyId)
      const index = this.filterItems.findIndex(item => item.property.bk_property_id === propertyId)
      if (index >= 0) {
        this.filterItems.splice(index, 1)
        if (this.filterItems.length === 0) {
          this.initDefaultItem()
        }
      }
    },
    updateConditionsFromMap(newConditionMap) {
      console.log('[GeneralModelFilter] updateConditionsFromMap:', newConditionMap)
      if (!newConditionMap || Object.keys(newConditionMap).length === 0) {
        this.clearAllConditions()
        return
      }
      
      const existingPropertyIds = this.filterItems.map(item => item.property.bk_property_id)
      const newPropertyIds = Object.keys(newConditionMap)
      
      const idsToRemove = existingPropertyIds.filter(id => !newPropertyIds.includes(id))
      idsToRemove.forEach(id => {
        const index = this.filterItems.findIndex(item => item.property.bk_property_id === id)
        if (index >= 0) {
          this.filterItems.splice(index, 1)
        }
      })
      
      newPropertyIds.forEach(fieldId => {
        const existingIndex = this.filterItems.findIndex(item => item.property.bk_property_id === fieldId)
        const property = this.properties.find(p => p.bk_property_id === fieldId)
        
        if (!property) return
        
        const condition = newConditionMap[fieldId]
        const { operator, value } = condition
        
        const isEnumOrList = ['enum', 'enummulti', 'list'].includes(property.bk_property_type)
        const isDateTime = ['date', 'time'].includes(property.bk_property_type)
        
        let valueText = ''
        let valueRange = ''
        
        if (isEnumOrList || isDateTime) {
          const isInOp = this.isInOperator(operator)
          if (isInOp && typeof value === 'string') {
            valueText = value.split(',').map(v => v.trim()).filter(v => v)
          } else {
            valueText = Array.isArray(value) ? [...value] : []
          }
        } else if (this.isRangeOperator(operator)) {
          valueRange = Array.isArray(value) ? value.join('\n') : value
        } else if (this.isInOperator(operator)) {
          if (Array.isArray(value)) {
            valueText = value.join('\n')
          } else {
            valueText = String(value)
          }
        } else {
          valueText = Array.isArray(value) ? value.join(',') : value
        }
        
        if (existingIndex >= 0) {
          this.filterItems[existingIndex].operator = operator
          this.filterItems[existingIndex].valueText = valueText
          this.filterItems[existingIndex].valueRange = valueRange
        }
      })
      
      if (this.filterItems.length === 0) {
        this.initDefaultItem()
      }
    }
  }
}</script>

<style lang="scss" scoped>
.general-model-filter-sideslider {
  :deep(.bk-sideslider-wrapper) {
    pointer-events: initial;
  }
}

.filter-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.filter-header {
  padding: 8px 14px;
  border-bottom: 1px solid #dcdee5;
  background: #fff;
  position: sticky;
  top: 0;
  z-index: 100;
}

.filter-operate {
  display: flex;
  align-items: center;
  justify-content: space-between;
  line-height: 30px;
}

.filter-footer {
  display: flex;
  gap: 10px;
  padding: 10px 24px;
  border-top: 1px solid #dcdee5;
  background: #fff;
  margin-top: auto;

  .bk-button {
    min-width: 88px;
  }
}

.filter-condition-list {
  flex: 1;
  overflow-y: auto;
  padding: 5px 14px;
}

.filter-item {
  padding: 2px 10px 10px;
  margin-top: 5px !important;
  position: relative;
  border-radius: 2px;
  max-width: 100%;
  box-sizing: border-box;

  &:hover {
    background: #f5f6fa;

    .item-remove {
      opacity: 1;
    }
  }

  &.is-last {
    margin-bottom: 20px;
  }

  .item-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
  }

  .item-label {
    flex: 1;
    font-size: 14px;
    font-weight: 400;
    line-height: 24px;
    color: #313238;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;

    .item-label-suffix {
      font-size: 12px;
      color: #979ba5;
    }
  }

  .item-content-wrapper {
    display: flex;
    align-items: flex-start;
    min-height: 32px;
  }

  .item-operator {
    flex: 128px 0 0;
    margin-right: 8px;

    :deep(.bk-select-trigger) {
      font-size: 12px;
    }

    & ~ .item-value {
      max-width: calc(100% - 136px);
    }
  }

  .item-value {
    flex: 1;
    min-width: 0;
    position: relative;

    &.is-full {
      width: 100%;
    }

    :deep(.bk-textarea) {
      textarea {
        resize: vertical;
        min-height: 32px;
      }
    }
    
    :deep(.bk-select-tag-container) {
      flex-wrap: wrap;
    }
  }

  .item-remove {
    width: 24px;
    height: 24px;
    display: flex;
    justify-content: center;
    align-items: center;
    margin-left: 8px;
    font-size: 20px;
    opacity: 0;
    cursor: pointer;
    color: #63656e;
    transition: opacity 0.2s;
    flex-shrink: 0;

    &:hover {
      color: #ea3636;
    }
  }
}

.add-condition-btn {
  padding-left: 10px;
  font-size: 12px;

  .bk-icon {
    margin-right: 4px;
  }
}

.clear-btn {
  font-size: 12px;
}

@media (max-width: 768px) {
  .filter-header,
  .filter-footer {
    padding: 12px 16px;
  }

  .filter-condition-list {
    padding: 5px 10px;
  }

  .filter-item {
    padding: 6px 10px 10px;

    .item-header {
      margin-bottom: 6px;
    }

    .item-label {
      font-size: 13px;
    }

    .item-content-wrapper {
      flex-direction: column;
    }

    .item-operator {
      flex: auto;
      width: 100%;
      margin-bottom: 8px;
      margin-right: 0;

      & ~ .item-value {
        max-width: 100%;
      }
    }

    .item-value {
      width: 100%;
      position: relative;
    }

    .item-remove {
      opacity: 1;
    }
  }
}
</style>
