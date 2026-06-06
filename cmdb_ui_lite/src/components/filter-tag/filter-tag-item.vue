<template>
  <span class="filter-tag" @click="handleClick">
    <label class="tag-name">{{ propertyName || property.bk_property_name }}</label>
    <span class="tag-colon" v-if="showColon">:</span>
    <span class="tag-value" v-bk-tooltips="{ content: displayText, trigger: 'hover' }">
      {{ displayText }}
    </span>
    <i class="tag-delete bk-icon icon-close" @mouseenter.prevent.stop @click.stop="handleRemove"></i>
  </span>
</template>

<script>
import { getOperatorSymbol } from '@/utils/query-operator'

export default {
  name: 'FilterTagItem',
  props: {
    property: {
      type: Object,
      default: () => ({})
    },
    operator: {
      type: String,
      default: '$eq'
    },
    value: {
      type: [String, Array, Number, Boolean],
      default: ''
    },
    propertyName: {
      type: String,
      default: ''
    }
  },
  computed: {
    showColon() {
      return this.operator === '$range'
    },
    operatorSymbol() {
      return getOperatorSymbol(this.operator)
    },
    transformedValue() {
      let { value } = this
      if (!Array.isArray(value)) {
        value = [value]
      }
      return value.map(v => {
        if (v === null || v === undefined) {
          return ''
        }
        return String(v)
      }).filter(v => v.length > 0)
    },
    getEnumDisplayValue(id) {
      const option = this.property.option || this.property.bk_property_option
      if (option && Array.isArray(option) && option.length > 0) {
        if (option[0] && typeof option[0] === 'object' && option[0].id !== undefined) {
          const opt = option.find(o => o.id === id || o.id === String(id))
          if (opt) {
            return opt.name
          }
        } else if (typeof option[0] === 'string') {
          // 旧格式，直接返回 id
          return id
        }
      }
      return id
    },
    displayText() {
      const propertyType = this.property.bk_property_type
      
      // 处理枚举类型，显示名称而不是 ID
      let displayValues = this.transformedValue
      if (propertyType === 'enum' || propertyType === 'list') {
        displayValues = this.transformedValue.map(v => this.getEnumDisplayValue(v))
      }
      
      if (this.operator === '$range') {
        const [start, end] = displayValues
        return `${start} ~ ${end}`
      }
      return `${this.operatorSymbol} ${displayValues.join(' | ')}`
    }
  },
  methods: {
    handleClick() {
      this.$emit('click')
    },
    handleRemove() {
      this.$emit('remove')
    }
  }
}
</script>

<style lang="scss" scoped>
.filter-tag {
  display: inline-flex;
  align-items: center;
  margin: 0 3px 10px;
  padding: 0 0 0 5px;
  border-radius: 2px;
  font-size: 12px;
  background: #f0f1f5;
  line-height: 22px;
  cursor: pointer;
  max-width: 100%;

  &:hover {
    background-color: #DCDEE5;
  }

  .tag-name {
    max-width: 150px;
    padding-right: 5px;
    color: #63656E;
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .tag-colon {
    padding-right: 5px;
    flex-shrink: 0;
  }

  .tag-value {
    max-width: 180px;
    color: #313238;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex-shrink: 1;
  }

  .tag-delete {
    font-size: 18px;
    color: #9b9ea8;
    cursor: pointer;
    margin-left: 5px;
    margin-right: 5px;
    line-height: 22px;
    flex-shrink: 0;

    &:hover {
      color: #313238;
    }
  }
}
</style>
