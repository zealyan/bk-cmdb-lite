<template>
  <bk-sideslider
    class="filter-form-sideslider"
    :is-show.sync="isShow"
    :width="400"
    :show-mask="false"
    :transfer="transfer"
    :before-close="handleSliderBeforeClose"
    @hidden="handleHidden">
    <div class="filter-form-header" slot="header">
      高级筛选
    </div>
    <div class="filter-layout" slot="content" ref="propertyList">
      <bk-form class="filter-form" form-type="vertical">
        <bk-form-item class="filter-ip filter-item">
          <label class="item-label">
            IP
          </label>
          <div class="ip-input-wrapper">
            <bk-input
              class="ip-input"
              type="textarea"
              :rows="3"
              v-model="IPCondition.text"
              :placeholder="editBlockPlaceholder">
            </bk-input>
          </div>
          <div class="ip-options">
            <bk-checkbox class="mr20" v-model="IPCondition.inner" @change="handleIPOptionChange('outer', ...arguments)">
              内网IP
            </bk-checkbox>
            <bk-checkbox class="mr20" v-model="IPCondition.outer" @change="handleIPOptionChange('inner', ...arguments)">
              外网IP
            </bk-checkbox>
            <bk-checkbox v-model="IPCondition.exact">精确</bk-checkbox>
          </div>
          <div class="filter-operate">
            <condition-picker
              ref="conditionPicker"
              :text="conditionText"
              :icon="icon"
              :selected="selected"
              :property-map="propertyMap"
              :type="3"
              @change="handleConditionPickerChange">
            </condition-picker>
            <bk-popconfirm
              content="确定清空筛选条件"
              width="280"
              trigger="click"
              confirm-text="确定"
              cancel-text="取消"
              @confirm="handleClearCondition">
              <bk-button :text="true" class="mr10" theme="primary"
                :disabled="!selected.length">
                清空条件
              </bk-button>
            </bk-popconfirm>
          </div>
        </bk-form-item>

        <bk-form-item
          class="filter-item"
          v-for="(property, index) in selected"
          :key="property.bk_property_id"
          :class="[`filter-item-${property.bk_property_type}`, { 'last-item': index === selected.length - 1 && scrollToBottom }]">
          <label class="item-label">
            {{ property.bk_property_name }}
            <span class="item-label-suffix">({{ getLabelSuffix(property) }})</span>
          </label>
          <div class="item-content-wrapper">
            <operator-selector
              class="item-operator"
              v-if="!withoutOperator.includes(property.bk_property_type)"
              :property="property"
              :custom-type-map="customOperatorTypeMap"
              :symbol-map="operatorSymbolMap"
              :desc-map="operatorDescMap"
              v-model="condition[property.bk_property_id].operator"
              @change="handleOperatorChange(property, ...arguments)">
            </operator-selector>
            <component
              class="item-value r0"
              :is="getComponentName(property)"
              :placeholder="getPlaceholder(property)"
              :property="property"
              :ref="`component-${property.bk_property_id}`"
              v-model.trim="condition[property.bk_property_id].value"
              @change="handleChange"
              @inputchange="handleInputChange">
            </component>
          </div>
          <i class="item-remove bk-icon icon-close" @click="handleRemove(property)"></i>
        </bk-form-item>
      </bk-form>

      <div class="filter-options">
        <bk-button
          class="option-search mr10 search-btn"
          theme="primary"
          @click="handleSearch">
          查询
        </bk-button>
        <bk-button class="option-reset" theme="default" @click="handleReset">清空</bk-button>
      </div>
    </div>
  </bk-sideslider>
</template>

<script>
import isEqual from 'lodash/isEqual'
import FilterStore from './store'
import Utils from './utils'
import OperatorSelector from './operator-selector.vue'
import ConditionPicker from '@/components/condition-picker/index.vue'
import { QUERY_OPERATOR, QUERY_OPERATOR_SYMBOL, QUERY_OPERATOR_DESC } from '@/utils/query-operator'
import { getConditionSelect, updatePropertySelect, isPasteSplit } from '@/utils/util'

export default {
  name: 'FilterForm',
  components: {
    OperatorSelector,
    ConditionPicker,
    SimpleTextInput: () => import('./simple-inputs/simple-text-input.vue'),
    SimpleNumberInput: () => import('./simple-inputs/simple-number-input.vue'),
    SimpleEnumSelect: () => import('./simple-inputs/simple-enum-select.vue'),
    SimpleDatePicker: () => import('./simple-inputs/simple-date-picker.vue'),
    SimpleTimePicker: () => import('./simple-inputs/simple-time-picker.vue'),
    SimpleDateTimePicker: () => import('./simple-inputs/simple-datetime-picker.vue'),
    SimpleBoolSelect: () => import('./simple-inputs/simple-bool-select.vue')
  },
  props: {
    type: {
      type: String,
      default: ''
    },
    searchAction: {
      type: Function,
      default: () => {}
    },
    icon: {
      type: String,
      default: ''
    },
    conditionText: {
      type: String,
      default: '添加其他条件'
    },
    transfer: {
      type: Boolean,
      default: true
    }
  },
  data() {
    const { IN, NIN, LIKE, CONTAINS, EQ, NE, GTE, LTE, RANGE } = QUERY_OPERATOR
    return {
      scrollToBottom: false,
      isShow: false,
      withoutOperator: ['date', 'time', 'bool'],
      IPCondition: Utils.getDefaultIP(),
      originIPCondition: { ...FilterStore.IP },
      condition: {},
      originCondition: {},
      selected: [],
      customOperatorTypeMap: {
        float: [EQ, NE, GTE, LTE, RANGE, IN],
        int: [EQ, NE, GTE, LTE, RANGE, IN],
        longchar: [IN, NIN, CONTAINS, LIKE],
        singlechar: [IN, NIN, CONTAINS, LIKE],
        shortchar: [IN, NIN, CONTAINS, LIKE],
        text: [IN, NIN, CONTAINS, LIKE],
        array: [IN, NIN, CONTAINS, LIKE],
        object: [IN, NIN, CONTAINS, LIKE]
      },
      operatorSymbolMap: QUERY_OPERATOR_SYMBOL,
      operatorDescMap: QUERY_OPERATOR_DESC
    }
  },
  computed: {
    editBlockPlaceholder() {
      const { exact } = this.IPCondition
      return exact ? '请输入IP，多个用换行分隔' : '请输入IP，支持模糊搜索'
    },
    propertyMap() {
      let modelPropertyMap = { ...FilterStore.modelPropertyMap }
      const ignoreHostProperties = ['bk_host_innerip', 'bk_host_outerip', 'bk_host_innerip_v6', 'bk_host_outerip_v6']
      if (modelPropertyMap.host) {
        modelPropertyMap.host = modelPropertyMap.host.filter(
          property => !ignoreHostProperties.includes(property.bk_property_id)
        )
      }
      return modelPropertyMap
    },
    storageSelected() {
      return FilterStore.selected
    },
    storageIPCondition() {
      return FilterStore.IP
    }
  },
  watch: {
    storageSelected: {
      immediate: true,
      handler(val) {
        const filterCondition = ['bk_host_innerip_v6', 'bk_host_outerip_v6']
        const { addSelect, deleteSelect } = getConditionSelect(val, this.selected)

        this.scrollToBottom = this.hasAddSelected(val, this.selected, addSelect)
        updatePropertySelect(this.selected, this.handleRemove, addSelect, deleteSelect, 'push', filterCondition)
        this.condition = this.initCondition()
      }
    },
    storageIPCondition: {
      immediate: true,
      handler() {
        this.IPCondition = {
          ...this.storageIPCondition
        }
      }
    }
  },
  created() {
    this.originCondition = this.setCondition(this.originCondition)
  },
  methods: {
    hasAddSelected(val, oldVal, addSelect) {
      return val[0] && oldVal[0] && addSelect.length > 0
    },
    handleClearCondition() {
      this.clearCondition()
      this.selected = []
      FilterStore.updateSelected([...this.selected])
      FilterStore.updateUserBehavior(this.selected)
    },
    handleChange() {
    },
    handleInputChange() {
    },
    setCondition(nowCondition) {
      const newCondition = { ...FilterStore.condition }
      Object.keys(nowCondition).forEach(id => {
        if (Object.prototype.hasOwnProperty.call(nowCondition, id)) {
          newCondition[id] = nowCondition[id]
        }
      })
      return newCondition
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
      return newCondition
    },
    getLabelSuffix(property) {
      const modelNameMap = {
        host: '主机',
        module: '模块',
        set: '集群',
        biz: '业务'
      }
      return modelNameMap[property.bk_obj_id] || property.bk_obj_id
    },
    getComponentName(property) {
      const type = property.bk_property_type
      const condition = this.condition[property.bk_property_id] || {}
      const { operator } = condition
      const normal = this.getSimpleComponentName(type)

      if (Utils.numberUseIn(property, operator)) {
        return 'SimpleTextInput'
      }

      return normal
    },
    getSimpleComponentName(type) {
      const componentMap = {
        singlechar: 'SimpleTextInput',
        shortchar: 'SimpleTextInput',
        longchar: 'SimpleTextInput',
        text: 'SimpleTextInput',
        textarea: 'SimpleTextInput',
        char: 'SimpleTextInput',
        int: 'SimpleNumberInput',
        float: 'SimpleNumberInput',
        double: 'SimpleNumberInput',
        long: 'SimpleNumberInput',
        enum: 'SimpleEnumSelect',
        enummulti: 'SimpleEnumSelect',
        list: 'SimpleEnumSelect',
        date: 'SimpleDatePicker',
        time: 'SimpleTimePicker',
        datetime: 'SimpleDateTimePicker',
        bool: 'SimpleBoolSelect'
      }
      return componentMap[type] || 'SimpleTextInput'
    },
    getPlaceholder(property) {
      return Utils.getPlaceholder(property)
    },
    handleIPOptionChange(negativeType, value) {
      if (!(value || this.IPCondition[negativeType])) {
        this.IPCondition[negativeType] = true
      }
    },
    handleOperatorChange(property, operator) {
      const condition = this.condition[property.bk_property_id]
      if (!condition) return
      const { value } = condition
      const effectValue = Utils.getOperatorSideEffect(property, operator, value)
      condition.value = effectValue
    },
    async handleRemove(property) {
      const index = this.selected.indexOf(property)
      index > -1 && this.selected.splice(index, 1)
      await this.$nextTick()
      FilterStore.updateSelected([...this.selected])
      FilterStore.updateUserBehavior(this.selected)
    },
    handleConditionPickerChange(selected) {
      const currentIds = this.selected.map(item => item.bk_property_id)
      selected.forEach(property => {
        if (!currentIds.includes(property.bk_property_id)) {
          this.selected.push(property)
          if (!this.condition[property.bk_property_id]) {
            const defaultOperator = this.getDefaultOperator(property)
            const operators = this.getOperators(property)
            const operator = operators.length > 0 ? operators.find(op => op.id === defaultOperator)?.id || operators[0].id : defaultOperator
            this.$set(this.condition, property.bk_property_id, {
              operator,
              value: ''
            })
          }
        }
      })
      const selectedIds = selected.map(p => p.bk_property_id)
      this.selected = this.selected.filter(item => selectedIds.includes(item.bk_property_id))
      Object.keys(this.condition).forEach(id => {
        if (!selectedIds.includes(id)) {
          delete this.condition[id]
        }
      })
      FilterStore.updateSelected([...this.selected])
      FilterStore.updateUserBehavior(this.selected)
    },
    getDefaultOperator(property) {
      const type = property.bk_property_type
      const defaultMap = {
        singlechar: '$in',
        shortchar: '$in',
        longchar: '$in',
        text: '$in',
        int: '$eq',
        float: '$eq',
        enum: '$in',
        enummulti: '$in',
        list: '$in',
        bool: '$eq',
        date: '$range',
        time: '$range',
        objuser: '$in',
        organization: '$in',
        timezone: '$in',
        foreignkey: '$in',
        array: '$in',
        object: '$in'
      }
      return defaultMap[type] || '$eq'
    },
    getOperators(property) {
      const type = property.bk_property_type
      const operatorsMap = {
        float: ['$eq', '$ne', '$gte', '$lte', '$range', '$in'],
        int: ['$eq', '$ne', '$gte', '$lte', '$range', '$in'],
        longchar: ['$in', '$nin', '$contains', '$regex'],
        singlechar: ['$in', '$nin', '$contains', '$regex'],
        shortchar: ['$in', '$nin', '$contains', '$regex'],
        text: ['$in', '$nin', '$contains', '$regex'],
        array: ['$in', '$nin', '$contains', '$regex'],
        object: ['$in', '$nin', '$contains', '$regex'],
        enum: ['$in', '$nin', '$eq'],
        enummulti: ['$in', '$nin'],
        list: ['$in', '$nin'],
        date: ['$gte', '$lte', '$range'],
        time: ['$gte', '$lte', '$range'],
        bool: ['$eq', '$ne']
      }
      return (operatorsMap[type] || ['$eq']).map(op => ({ id: op, name: op, desc: op }))
    },
    handleSearch() {
      this.searchTimer && clearTimeout(this.searchTimer)
      this.searchTimer = setTimeout(() => {
        const condition = {
          condition: JSON.parse(JSON.stringify(this.condition)),
          IP: JSON.parse(JSON.stringify(this.IPCondition))
        }
        if (this.type === 'index') {
          return this.searchAction(condition)
        }

        FilterStore.resetPage(true)
        FilterStore.updateSelected([...this.selected])
        FilterStore.setCondition(condition)
        this.close()
      }, 300)
    },
    handleReset() {
      this.IPCondition = Utils.getDefaultIP()
      this.clearCondition()
    },
    clearCondition() {
      Object.keys(this.condition).forEach(id => {
        const property = this.selected.find(p => p.bk_property_id?.toString() === id?.toString())
        const propertyCondition = this.condition[id]
        if (propertyCondition) {
          const defaultValue = Utils.getOperatorSideEffect(property, propertyCondition.operator, '')
          propertyCondition.value = defaultValue
        }
      })
    },
    handleSliderBeforeClose() {
      const changedIPCondition = !isEqual(this.IPCondition, this.originIPCondition)
      const changedCondition = !isEqual(this.condition, this.originCondition)

      if (changedIPCondition || changedCondition) {
        this.$bkInfo({
          title: '提示',
          subTitle: '离开将会导致未保存信息丢失',
          extCls: 'bk-dialog-sub-header-center',
          confirmFn: () => {
            this.close()
          }
        })
        return false
      }
      this.close()
    },
    handleHidden() {
      this.$emit('closed')
    },
    open() {
      this.originIPCondition = { ...this.IPCondition }
      this.originCondition = JSON.parse(JSON.stringify(this.condition))
      this.isShow = true
    },
    close() {
      this.isShow = false
    },
    focusIP() {
      const ipInput = this.$el?.querySelector('.ip-input textarea')
      if (ipInput) {
        ipInput.focus()
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.filter-form-sideslider {
  ::v-deep .bk-sideslider-wrapper {
    pointer-events: initial;
  }
}

.filter-form-header {
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.filter-layout {
  height: 100%;
  overflow-y: auto;
}

.filter-form {
  padding: 0 14px;
}

.filter-ip {
  padding: 7px 10px 0px !important;
  position: sticky;
  top: 0;
  z-index: 9999;
  background: white;

  .filter-operate {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 10px;
  }
}

.ip-input-wrapper {
  .ip-input {
    :deep(.bk-textarea) {
      resize: vertical;
      min-height: 82px;
    }

    :deep(.bk-form-control) {
      font-size: 12px;
      line-height: 24px;
    }
  }
}

.ip-options {
  margin-top: 10px;
  font-size: 12px;
}

.filter-item {
  padding: 2px 10px 10px;

  &:not(.filter-ip):hover {
    background: #f5f6fa;
    .item-remove {
      opacity: 1;
    }
  }

  .item-label {
    display: block;
    font-size: 14px;
    font-weight: 400;
    line-height: 24px;
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

    & ~ .item-value {
      max-width: calc(100% - 136px);
    }
  }

  .item-value {
    flex: 1;
  }

  .item-remove {
    position: absolute;
    width: 24px;
    height: 24px;
    display: flex;
    justify-content: center;
    align-items: center;
    right: -10px;
    top: 3px;
    font-size: 20px;
    opacity: 0;
    cursor: pointer;
    color: #63656e;

    &:hover {
      color: #ea3636;
    }
  }
}

.filter-options {
  display: flex;
  align-items: center;
  padding: 10px 24px;

  &.is-sticky {
    border-top: 1px solid #dcdee5;
    background-color: #fff;
  }

  .option-reset {
    margin-left: auto;
  }
}

.option-search {
  min-width: 80px;
}

.mr10 {
  margin-right: 10px;
}

.r0 {
  border-radius: 0;
}
</style>