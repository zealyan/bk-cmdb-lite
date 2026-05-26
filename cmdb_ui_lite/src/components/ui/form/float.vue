<template>
  <bk-input
    v-model="localValue"
    type="number"
    :placeholder="placeholder"
    :disabled="disabled || readonly"
    :min="min"
    :max="max"
    :step="step"
    @change="handleChange">
  </bk-input>
</template>

<script>
export default {
  name: 'cmdb-form-float',
  props: {
    value: {
      default: null
    },
    property: {
      type: Object,
      default: () => ({})
    },
    disabled: Boolean,
    readonly: Boolean
  },
  data() {
    return {
      localValue: null
    }
  },
  computed: {
    placeholder() {
      return this.property.placeholder || `请输入${this.property.bk_property_name || ''}`
    },
    min() {
      return this.property.option?.min ?? -Infinity
    },
    max() {
      return this.property.option?.max ?? Infinity
    },
    step() {
      return this.property.option?.step || 0.01
    }
  },
  watch: {
    value: {
      immediate: true,
      handler(val) {
        this.localValue = val
      }
    }
  },
  methods: {
    handleChange(val) {
      const numVal = val === '' ? null : parseFloat(val)
      this.$emit('input', isNaN(numVal) ? null : numVal)
    }
  }
}
</script>
