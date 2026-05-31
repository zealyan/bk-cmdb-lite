<template>
  <bk-sideslider
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
            <div class="item-value" :class="{ 'is-full': withoutOperator.includes(item.property.bk_property_type), 'r0': ['cmdb-search-enum', 'cmdb-search-list', 'cmdb-search-date', 'cmdb-search-time'].includes(getComponentType(item)) }">
              <component
                :is="getComponentType(item)"
                v-if="['cmdb-search-enum', 'cmdb-search-list'].includes(getComponentType(item))"
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
              <bk-select
                v-else-if="getComponentType(item) === 'select'"
                v-model="item.valueText"
                :placeholder="getPlaceholder(item)"
                :options="getSelectOptions(item.property)"
                searchable
                size="small">
              </bk-select>
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
import ListSearch from '../search/list.vue'
import DateSearch from '../search/date.vue'
import TimeSearch from '../search/time.vue'
import { transformGeneralModelCondition, getOperatorSideEffect } from './utils'
import { setSearchQueryByCondition, buildSearchParams } from '@/utils/query-builder'

const { EQ, NE, IN, NIN, GT, LT, GTE, LTE, RANGE, LIKE } = QUERY_OPERATOR

export default {
  name: 'GeneralModelFilter',
  components: {
    ConditionPicker,
    'cmdb-search-enum': EnumSearch,
    'cmdb-search-list': ListSearch,
    'cmdb-search-date': DateSearch,
    'cmdb-search-time': TimeSearch
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
    }
  },
  data() {
    return {
      isShow: false,
      filterItems: [],
      nextItemId: 1,
      withoutOperator: ['bool', 'date', 'time'],
      operatorsMap: {
        float: [EQ, NE, GT, LT, GTE, LTE, RANGE, IN],
        int: [EQ, NE, GT, LT, GTE, LTE, RANGE, IN],
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
        object: [IN, NIN, LIKE]
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
      const availableProperties = this.properties.filter(p => {
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
        if (val && this.filterItems.length === 0) {
          this.initDefaultItem()
        }
      }
    },
    isShow(val) {
      this.$emit('update:show', val)
    }
  },
  methods: {
    getItemValue(item) {
      if (this.isRangeOperator(item.operator)) {
        return item.valueRange || ''
      }
      const isEnumOrList = ['enum', 'list'].includes(item.property.bk_property_type)
      const isDateTime = ['date', 'time'].includes(item.property.bk_property_type)
      if (isEnumOrList || isDateTime) {
        return item.valueText || []
      }
      if (this.isInOperator(item.operator)) {
        return item.valueText || ''
      }
      return item.valueText || ''
    },
    initDefaultItem() {
      if (this.properties.length > 0) {
        const sortedProperties = [...this.properties]
          .filter(p => p.bk_property_index >= 0)
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
        return 'select'
      }

      const inputTypes = ['int', 'float', 'singlechar', 'longchar', 'objuser', 'organization', 'timezone', 'foreignkey', 'array', 'object', 'map', 'table']
      const textareaTypes = ['text']
      const selectTypes = ['bool']

      if (selectTypes.includes(type)) {
        return 'select'
      }
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
      const option = property.option || property.bk_property_option
      if (option && Array.isArray(option)) {
        if (property.bk_property_type === 'enum') {
          return option.map(opt => ({
            id: opt,
            name: opt
          }))
        }
        return option
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

      const isEnumOrList = ['enum', 'list'].includes(property.bk_property_type)
      const isDateTime = ['date', 'time'].includes(property.bk_property_type)
      this.filterItems.push({
        id: this.nextItemId++,
        property,
        operator,
        valueText: isEnumOrList || isDateTime ? [] : '',
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
      const isEnumOrList = ['enum', 'list'].includes(item.property.bk_property_type)
      const isDateTime = ['date', 'time'].includes(item.property.bk_property_type)
      item.valueText = isEnumOrList || isDateTime ? [] : ''
      item.valueRange = ''
    },
    handleSearch() {
      const conditionMap = {}

      this.filterItems.forEach(item => {
        const value = this.getItemValue(item)
        const isEnumOrList = ['enum', 'list'].includes(item.property.bk_property_type)
        const isDateTime = ['date', 'time'].includes(item.property.bk_property_type)

        if (isEnumOrList || isDateTime) {
          if (Array.isArray(value) && value.length > 0) {
            conditionMap[item.property.bk_property_id] = {
              operator: item.operator,
              value
            }
          }
        } else if (value !== null && value !== undefined && String(value).trim().length > 0) {
          let processedValue = value

          if (this.isInOperator(item.operator) && !isEnumOrList) {
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
    }
  }
}
</script>

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
