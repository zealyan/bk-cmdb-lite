<template>
  <bk-select
    :model-value="modelValue"
    :placeholder="'请选择'"
    :options="options"
    @change="handleChange">
  </bk-select>
</template>

<script>
export default {
  name: 'OperatorSelector',
  props: {
    modelValue: {
      type: String,
      default: ''
    },
    property: {
      type: Object,
      required: true
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
    options() {
      const type = this.property.bk_property_type
      const operators = this.customTypeMap[type] || []
      return operators.map(op => ({
        label: `${this.symbolMap[op]} ${this.descMap[op]}`,
        value: op
      }))
    }
  },
  methods: {
    handleChange(value) {
      this.$emit('update:modelValue', value)
      this.$emit('change', value)
    }
  }
}
</script>