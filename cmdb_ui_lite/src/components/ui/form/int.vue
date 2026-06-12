<template>
  <div class="cmdb-form-int-wrapper">
    <bk-input
      v-model="localValue"
      type="number"
      :placeholder="placeholder"
      :disabled="disabled || readonly"
      @change="handleChange"
      @blur="handleBlur">
      <template slot="append" v-if="unit">
        <span class="input-unit">{{ unit }}</span>
      </template>
    </bk-input>
    <div class="error-hint" v-if="errorMessage">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script>
import { parseOption } from '@/utils/validate-utils'

export default {
  name: 'cmdb-form-int',
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
      localValue: null,
      errorMessage: ''
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
    }
  },
  watch: {
    value: {
      immediate: true,
      handler(val) {
        this.localValue = val
        this.errorMessage = ''
      }
    }
  },
  methods: {
    handleChange(val) {
      const numVal = val === '' || val === null ? null : Number(val)
      this.$emit('input', numVal)
      if (numVal !== null) {
        this.validateValue(numVal)
      } else {
        this.errorMessage = ''
      }
    },
    handleBlur() {
      if (this.localValue !== null && this.localValue !== '') {
        this.validateValue(Number(this.localValue))
      }
    },
    validateValue(value) {
      if (!Number.isInteger(value)) {
        this.errorMessage = '请输入整数'
        return false
      }
      const errors = []
      if (this.min !== -Infinity && value < this.min) {
        errors.push(`最小值为 ${this.min}`)
      }
      if (this.max !== Infinity && value > this.max) {
        errors.push(`最大值为 ${this.max}`)
      }
      if (errors.length > 0) {
        this.errorMessage = errors[0]
        return false
      }
      this.errorMessage = ''
      return true
    },
    validate() {
      if (this.localValue === null || this.localValue === '') {
        return true
      }
      return this.validateValue(Number(this.localValue))
    },
    clearError() {
      this.errorMessage = ''
    }
  }
}
</script>

<style lang="scss" scoped>
.cmdb-form-int-wrapper {
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
  .error-hint {
    font-size: 12px;
    color: #ff5656;
    margin-top: 4px;
    line-height: 1.4;
  }
}
</style>
