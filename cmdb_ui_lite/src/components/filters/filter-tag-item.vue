<template>
  <span class="filter-tag" @click="handleClick">
    <label class="tag-name">{{property.bk_property_name}}</label>
    <span class="tag-colon" v-if="showColon">:</span>
    <span class="tag-value" v-bk-overflow-tips="tipsConfig">
      {{displayText}}
    </span>
    <i class="tag-delete bk-icon icon-close" @mouseenter.prevent.stop @click.stop="handleRemove"></i>
  </span>
</template>

<script>
import FilterStore from './store'
import Utils from './utils'
import FilterForm from './filter-form.js'
import { formatPropertyValue } from '@/utils/property-value'

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
    }
  },
  data() {
    return {
      tipsConfig: {
        triggerTarget: null,
        interactive: false,
        hideOnClick: false,
        allowHTML: true
      }
    }
  },
  computed: {
    showColon() {
      return this.operator === '$range'
    },
    operatorSymbol() {
      return Utils.getOperatorSymbol(this.operator) || this.operator.replace('$', '')
    },
    displayText() {
      // 多值统一为数组；枚举 / 列表 / 多选枚举类型按 option 映射为显示名（如 1 -> Linux），
      // 空值跳过。其余类型（单字符 / 数值 / 时间等）保持原始值。
      const ENUM_TYPES = ['enum', 'enummulti', 'list']
      const isEnum = ENUM_TYPES.includes(this.property?.bk_property_type)
      const displayValue = (Array.isArray(this.value) ? this.value : [this.value])
        .map(v => (v === null || v === undefined ? '' : (isEnum ? formatPropertyValue(v, this.property) : String(v))))
        .filter(v => v !== '')
        .join(' | ')

      if (this.operator === '$range') {
        const [start, end] = (Array.isArray(this.value) ? this.value : [this.value])
        return `${start} ~ ${end}`
      }
      return `${this.operatorSymbol} ${displayValue}`
    }
  },
  mounted() {
    this.tipsConfig.triggerTarget = this.$el
  },
  methods: {
    handleClick() {
      FilterForm.show()
    },
    handleRemove() {
      FilterStore.resetValue(this.property)
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
  }

  .tag-colon {
    padding-right: 5px;
  }

  .tag-value {
    max-width: 220px;
    color: #313238;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tag-delete {
    font-size: 20px;
    color: #9b9ea8;

    &:hover {
      color: #313238;
    }
  }
}
</style>