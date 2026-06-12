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
    <!-- 范围提示 -->
    <div class="range-hint" v-if="rangeHint && !errorMessage">
      {{ rangeHint }}
    </div>
    <!-- 错误提示 -->
    <div class="error-hint" v-if="errorMessage">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script>
import { parseOption, getRangeHint, validateValue } from '@/utils/validate-utils'

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
    // 占位符
    placeholder() {
      return this.property.placeholder || `请输入${this.property.bk_property_name || ''}`
    },
    // 单位
    unit() {
      return this.property.unit || ''
    },
    // 解析后的 option
    parsedOption() {
      return parseOption(this.property.option)
    },
    // 最小值
    min() {
      if (!this.parsedOption || this.parsedOption.min === undefined || this.parsedOption.min === '' || this.parsedOption.min === null) {
        return -Infinity
      }
      return Number(this.parsedOption.min)
    },
    // 最大值
    max() {
      if (!this.parsedOption || this.parsedOption.max === undefined || this.parsedOption.max === '' || this.parsedOption.max === null) {
        return Infinity
      }
      return Number(this.parsedOption.max)
    },
    // 范围提示文本
    rangeHint() {
      return getRangeHint(this.property)
    }
  },
  watch: {
    value: {
      immediate: true,
      handler(val) {
        this.localValue = val
        // 初始化时清除错误
        this.errorMessage = ''
      }
    }
  },
  methods: {
    /**
     * 处理输入变化
     * @param {any} val - 输入值
     */
    handleChange(val) {
      const numVal = val === '' || val === null ? null : Number(val)
      this.$emit('input', numVal)
      
      // 实时校验（仅在输入时做基本校验，blur 时做完整校验）
      if (numVal !== null) {
        this.validateValue(numVal)
      } else {
        this.errorMessage = ''
      }
    },
    
    /**
     * 处理失焦事件 - 进行完整校验
     */
    handleBlur() {
      if (this.localValue !== null && this.localValue !== '') {
        this.validateValue(Number(this.localValue))
      }
    },
    
    /**
     * 校验值
     * @param {number} value - 待校验的值
     * @returns {boolean} 是否有效
     */
    validateValue(value) {
      // 检查是否为整数
      if (!Number.isInteger(value)) {
        this.errorMessage = '请输入整数'
        return false
      }
      
      // 范围校验
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
    
    /**
     * 外部调用：校验方法
     * @returns {boolean} 是否有效
     */
    validate() {
      if (this.localValue === null || this.localValue === '') {
        // 如果必填，由 form 组件校验
        return true
      }
      return this.validateValue(Number(this.localValue))
    },
    
    /**
     * 外部调用：清除错误
     */
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
  
  .range-hint {
    font-size: 12px;
    color: #979ba5;
    margin-top: 4px;
    line-height: 1.4;
  }
  
  .error-hint {
    font-size: 12px;
    color: #ff5656;
    margin-top: 4px;
    line-height: 1.4;
  }
}
</style>
