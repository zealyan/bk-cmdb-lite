<template>
  <div class="cmdb-form-float-wrapper">
    <bk-input
      v-model="localValue"
      type="number"
      :placeholder="placeholder"
      :disabled="disabled || readonly"
      :step="step"
      @change="handleChange"
      @blur="handleBlur">
      <template slot="append" v-if="unit">
        <span class="input-unit">{{ unit }}</span>
      </template>
    </bk-input>
  </div>
</template>

<script>
import { parseOption } from '@/utils/validate-utils'

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
    unit() {
      return this.property.unit || ''
    },
    parsedOption() {
      return parseOption(this.property.option)
    },
    min() {
      if (!this.parsedOption || this.parsedOption.min === undefined || this.parsedOption.min === '' || this.parsedOption.min === null) {
        return -Infinity
      }
      return Number(this.parsedOption.min)
    },
    max() {
      if (!this.parsedOption || this.parsedOption.max === undefined || this.parsedOption.max === '' || this.parsedOption.max === null) {
        return Infinity
      }
      return Number(this.parsedOption.max)
    },
    step() {
      return this.parsedOption?.step || 0.01
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
      const numVal = val === '' || val === null ? null : parseFloat(val)
      this.$emit('input', isNaN(numVal) ? null : numVal)
    },
    handleBlur() {
      this.$emit('blur')
    },
    validate() {
      if (this.localValue === null || this.localValue === '') {
        return true
      }
      const numVal = parseFloat(this.localValue)
      if (isNaN(numVal)) {
        return false
      }
      if (this.min !== -Infinity && numVal < this.min) {
        return false
      }
      if (this.max !== Infinity && numVal > this.max) {
        return false
      }
      return true
    }
  }
}
</script>

<style lang="scss" scoped>
.cmdb-form-float-wrapper {
  position: relative;
  width: 100%;
  .input-unit {
    color: #63656e;
    font-size: 12px;
    padding: 0 8px;
    background: #f5f7fa;
    border-left: 1px solid #c4c6cc;
    height: 100%;
    display: flex;
    align-items: center;
  }
}
</style>
