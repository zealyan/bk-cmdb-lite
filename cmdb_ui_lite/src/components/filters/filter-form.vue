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
      <template v-if="collection">
        ({{collection.name}})
      </template>
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
              :placeholder="editBlockPlaceholder"
              @paste="handleIPPaste">
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
              :operator="condition[property.bk_property_id]?.operator || ''"
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
        <template v-if="collection">
          <span
            class="option-collect-wrapper"
            v-bk-tooltips="{
              disabled: allowCollect,
              content: '请先填写筛选条件'
            }">
            <bk-button
              class="option-collect"
              theme="default"
              :disabled="!allowCollect"
              @click="handleUpdateCollection">
              更新条件
            </bk-button>
          </span>
        </template>
        <bk-popover
          v-else
          class="option-collect"
          ref="collectionPopover"
          placement="top-end"
          theme="light"
          trigger="manual"
          :width="280"
          :z-index="99999"
          :tippy-options="{
            interactive: true,
            hideOnClick: false,
            boundary: 'window',
            onShown: focusCollectionName,
            onHidden: clearCollectionName
          }"
          v-bk-tooltips="{
            disabled: allowCollect,
            content: '请先填写筛选条件'
          }">
          <bk-button
            theme="default"
            :disabled="!allowCollect"
            @click="handleCreateCollection">
            收藏此条件
          </bk-button>
          <section class="collection-form" slot="content">
            <label class="collection-title">收藏此条件</label>
            <bk-input
              class="collection-name"
              ref="collectionName"
              placeholder="请填写名称"
              v-model.trim="collectionForm.name"
              @focus="handleCollectionFormFocus"
              @enter="handleSaveCollection">
            </bk-input>
            <p class="collection-error" v-if="collectionForm.error">{{collectionForm.error}}</p>
            <div class="collection-options">
              <bk-button
                class="mr10"
                theme="primary"
                size="small"
                :disabled="!collectionForm.name.length"
                :loading="collectionSaving"
                @click="handleSaveCollection">
                确定
              </bk-button>
              <bk-button theme="default" size="small" @click="closeCollectionForm">取消</bk-button>
            </div>
          </section>
        </bk-popover>
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
      const { IN, NIN, CONTAINS, CONTAINS_CS, EQ, NE, GTE, LTE, RANGE } = QUERY_OPERATOR
    return {
      scrollToBottom: false,
      isShow: false,
      withoutOperator: ['date', 'time', 'bool'],
      collectionForm: {
        name: '',
        error: ''
      },
      collectionSaving: false,
      IPCondition: Utils.getDefaultIP(),
      originIPCondition: { ...FilterStore.IP },
      condition: {},
      originCondition: {},
      selected: [],
      customOperatorTypeMap: {
        float: [EQ, NE, GTE, LTE, RANGE, IN],
        int: [EQ, NE, GTE, LTE, RANGE, IN],
        longchar: [IN, NIN, CONTAINS, CONTAINS_CS],
        singlechar: [IN, NIN, CONTAINS, CONTAINS_CS],
        shortchar: [IN, NIN, CONTAINS, CONTAINS_CS],
        text: [IN, NIN, CONTAINS, CONTAINS_CS],
        array: [IN, NIN, CONTAINS, CONTAINS_CS],
        object: [IN, NIN, CONTAINS, CONTAINS_CS]
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
    },
    collection() {
      return FilterStore.activeCollection
    },
    allowCollect() {
      const hasIP = !!(this.IPCondition.text && this.IPCondition.text.trim().length)
      const hasCondition = Object.keys(this.condition).some((id) => {
        const value = this.condition[id] && this.condition[id].value
        return value !== '' && value !== null && value !== undefined
          && !(Array.isArray(value) && value.length === 0)
      })
      return hasIP || hasCondition
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
      return val && val[0] && oldVal && oldVal[0] && addSelect && addSelect.length > 0
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
        } else if (Object.prototype.hasOwnProperty.call(FilterStore.condition, id)) {
          newCondition[id] = JSON.parse(JSON.stringify(FilterStore.condition[id]))
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
    handleIPPaste(event) {
      const text = event.clipboardData.getData('text')
      if (!text) return
      event.preventDefault()
      const values = Utils.splitIP(text)
      const currentText = this.IPCondition.text || ''
      const currentValues = currentText ? Utils.splitIP(currentText) : []
      const merged = [...new Set([...currentValues, ...values])]
      this.IPCondition.text = merged.join('\n')
    },
    handleOperatorChange(property, operator) {
      const condition = this.condition[property.bk_property_id]
      if (!condition) return
      const { value } = condition

      // 操作符切换时转换 value 类型
      let newValue = value
      const isArrayOp = ['$in', '$nin'].includes(operator)
      const wasArrayOp = ['$in', '$nin'].includes(condition.operator)

      if (isArrayOp && !wasArrayOp) {
        // 从非数组操作符切换到数组操作符：字符串 → 数组
        if (typeof value === 'string' && value.length > 0) {
          newValue = [value]
        } else if (!Array.isArray(value)) {
          newValue = []
        }
      } else if (!isArrayOp && wasArrayOp) {
        // 从数组操作符切换到非数组操作符：数组 → 字符串
        if (Array.isArray(value) && value.length > 0) {
          newValue = value[0]
        } else {
          newValue = ''
        }
      }

      const effectValue = Utils.getOperatorSideEffect(property, operator, newValue)
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
            const defaultData = Utils.getDefaultData(property)
            this.$set(this.condition, property.bk_property_id, {
              operator: defaultData.operator,
              value: defaultData.value
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
        longchar: ['$in', '$nin', '$contains', '$contains_s'],
        singlechar: ['$in', '$nin', '$contains', '$contains_s'],
        shortchar: ['$in', '$nin', '$contains', '$contains_s'],
        text: ['$in', '$nin', '$contains', '$contains_s'],
        array: ['$in', '$nin', '$contains', '$contains_s'],
        object: ['$in', '$nin', '$contains', '$contains_s'],
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
        // 深拷贝当前 condition 和 IP，避免引用问题
        const submitCondition = JSON.parse(JSON.stringify(this.condition))
        const submitIP = JSON.parse(JSON.stringify(this.IPCondition))
        if (this.type === 'index') {
          return this.searchAction({ condition: submitCondition, IP: submitIP })
        }

        FilterStore.resetPage(true)
        // 先 setCondition，再 updateSelected
        // 因为 updateSelected 会触发 watch -> initCondition，可能覆盖 condition
        // 所以先更新 selected，然后在 nextTick 中设置 condition
        FilterStore.updateSelected([...this.selected])
        this.$nextTick(() => {
          FilterStore.setCondition({
            condition: submitCondition,
            IP: submitIP
          })
          this.close()
        })
      }, 300)
    },
    handleReset() {
      this.IPCondition = Utils.getDefaultIP()
      this.clearCondition()
    },
    handleCreateCollection() {
      this.collectionForm.error = ''
      const popover = this.$refs.collectionPopover
      if (popover && popover.instance) {
        popover.instance.show()
      }
    },
    closeCollectionForm() {
      const popover = this.$refs.collectionPopover
      if (popover && popover.instance) {
        popover.instance.hide()
      }
      this.collectionForm.name = ''
      this.collectionForm.error = ''
    },
    handleCollectionFormFocus() {
      this.collectionForm.error = ''
    },
    focusCollectionName() {
      const ref = this.$refs.collectionName
      const input = (ref && ref.$refs && ref.$refs.input)
        || (ref && ref.$el && ref.$el.querySelector('input'))
      if (input && input.focus) {
        input.focus()
      }
    },
    clearCollectionName() {
      this.collectionForm.name = ''
      this.collectionForm.error = ''
    },
    async handleUpdateCollection() {
      try {
        const conditions = {}
        this.selected.forEach((property) => {
          const id = property.bk_property_id
          const cond = this.condition[id]
          if (cond) {
            conditions[id] = { operator: cond.operator, value: cond.value }
          }
        })
        await FilterStore.updateCollection({
          id: this.collection.id,
          name: this.collection.name,
          conditions
        })
        this.$success('更新收藏成功')
      } catch (e) {
        console.error('[filter-form] 更新收藏失败', e)
        const msg = (e && e.bk_error_msg) || '更新失败'
        this.$bkMessage && this.$bkMessage({ message: msg, theme: 'error' })
      }
    },
    async handleSaveCollection() {
      const name = (this.collectionForm.name || '').trim()
      // 必填校验（对齐上游 v-validate required）：空名称不提交，行内提示
      if (!name) {
        this.collectionForm.error = '请填写名称'
        return
      }
      this.collectionForm.error = ''
      // 从当前抽屉的 selected/condition 序列化 live 条件（不与 FilterStore.condition 的滞后状态耦合）
      const conditions = {}
      this.selected.forEach((property) => {
        const id = property.bk_property_id
        const cond = this.condition[id]
        if (cond) {
          conditions[id] = { operator: cond.operator, value: cond.value }
        }
      })
      this.collectionSaving = true
      try {
        await FilterStore.createCollection({ name, conditions })
        this.$success('收藏成功')
        this.closeCollectionForm()
      } catch (e) {
        console.error('[filter-form] 收藏条件失败', e)
        const msg = (e && e.bk_error_msg) || '收藏失败'
        this.collectionForm.error = msg
        this.$bkMessage && this.$bkMessage({ message: msg, theme: 'error' })
      } finally {
        this.collectionSaving = false
      }
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
      const storeCondition = {}
      this.selected.forEach((property) => {
        const id = property.bk_property_id
        if (Object.prototype.hasOwnProperty.call(FilterStore.condition, id)) {
          storeCondition[id] = JSON.parse(JSON.stringify(FilterStore.condition[id]))
        }
      })
      this.condition = { ...this.condition, ...storeCondition }
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

<!-- popover 内容被 teleport 到 body，scoped 样式无法命中，单独用非 scoped 块 -->
<style lang="scss">
.collection-form {
  .collection-title {
    display: block;
    font-size: 13px;
    color: #63656E;
    line-height: 17px;
  }

  .collection-name {
    margin-top: 13px;
  }

  .collection-error {
    color: #ea3636;
    position: absolute;
  }

  .collection-options {
    display: flex;
    padding: 20px 0 10px;
    justify-content: flex-end;
  }
}
</style>