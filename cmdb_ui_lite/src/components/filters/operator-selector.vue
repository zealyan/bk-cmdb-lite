<template>
  <bk-select
    v-model="localValue"
    v-bind="$attrs"
    v-on="listeners"
    :clearable="false">
    <bk-option v-for="(option, index) in options"
      class="operator-option"
      :key="index"
      :id="option.id"
      :name="option.name">
      <span>{{option.name}}</span>
    </bk-option>
  </bk-select>
</template>

<script>
import Utils from './utils'
import { QUERY_OPERATOR } from '@/utils/query-operator'

export default {
  name: 'OperatorSelector',
  props: {
    value: {
      type: String,
      default: ''
    },
    property: {
      type: Object,
      default: () => ({})
    },
    customTypeMap: {
      type: Object,
      default: () => ({})
    },
    symbolMap: {
      type: Object,
      default: () => ({})
    },
    descMap: {
      type: Object,
      default: () => ({})
    }
  },
  computed: {
    listeners() {
      const internalEvent = ['input', 'change']
      const listeners = {}
      Object.keys(this.$listeners).forEach((key) => {
        if (!internalEvent.includes(key)) {
          listeners[key] = this.$listeners[key]
        }
      })
      return listeners
    },
    options() {
      const { EQ, NE, IN, NIN, LT, GT, LTE, GTE, RANGE, CONTAINS_CS } = QUERY_OPERATOR
      const defaultTypeMap = {
        bool: [EQ, NE],
        date: [GTE, LTE],
        enum: [IN, NIN],
        enummulti: [IN, NIN],
        float: [EQ, NE, GT, LT, RANGE],
        int: [EQ, NE, GT, LT, RANGE],
        list: [IN, NIN],
        longchar: [IN, NIN, CONTAINS_CS],
        objuser: [IN, NIN],
        organization: [IN, NIN],
        singlechar: [IN, NIN, CONTAINS_CS],
        time: [GTE, LTE],
        timezone: [IN, NIN],
        foreignkey: [IN, NIN],
        table: [IN, NIN],
        array: [IN, NIN, CONTAINS_CS],
        object: [IN, NIN, CONTAINS_CS],
        map: [IN, NIN],
        shortchar: [IN, NIN, CONTAINS_CS],
        text: [IN, NIN, CONTAINS_CS],
        char: [IN, NIN, CONTAINS_CS],
        long: [EQ, NE, GT, LT, RANGE]
      }
      const typeMap = { ...defaultTypeMap, ...this.customTypeMap }
      const { bk_property_type: propertyType } = this.property
      const operators = typeMap[propertyType] || [EQ]
      return operators.map(operator => ({
        id: operator,
        name: Utils.getOperatorSymbol(operator, this.symbolMap) || operator.replace('$', '')
      }))
    },
    localValue: {
      get() {
        return this.value
      },
      set(value) {
        this.$emit('input', value)
        this.$emit('change', value)
      }
    }
  }
}
</script>