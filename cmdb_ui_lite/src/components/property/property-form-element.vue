<template>
  <div class="property-form-element">
    <!-- 文本输入框 -->
    <bk-input
      v-if="isTextType"
      ref="inputRef"
      type="text"
      :value="localValue"
      :placeholder="placeholder"
      :maxlength="maxCharLength"
      @input="handleInput"
      @blur="handleBlurAndValidate">
    </bk-input>

    <!-- 文本域 -->
    <bk-input
      v-else-if="property.bk_property_type === 'longchar'"
      ref="inputRef"
      type="textarea"
      :value="localValue"
      :placeholder="placeholder"
      :maxlength="maxCharLength"
      :rows="3"
      @input="handleInput"
      @blur="handleBlurAndValidate">
    </bk-input>

    <!-- 整数/浮点数 -->
    <bk-input
      v-else-if="isNumberType"
      ref="inputRef"
      type="number"
      :value="localValue"
      :placeholder="placeholder"
      @input="handleInput"
      @blur="handleBlurAndValidate">
    </bk-input>

    <!-- 枚举类型（单选） -->
    <cmdb-form-enum
      v-else-if="property.bk_property_type === 'enum'"
      ref="inputRef"
      :value="localValue"
      :property="property"
      :multiple="false"
      :placeholder="placeholder"
      @input="handleSelect"
      @on-selected="handleSelect">
    </cmdb-form-enum>

    <!-- 多选枚举类型 -->
    <cmdb-form-enummulti
      v-else-if="property.bk_property_type === 'enummulti'"
      ref="inputRef"
      :value="localValue"
      :property="property"
      :multiple="true"
      :placeholder="placeholder"
      @input="handleMultiSelect"
      @on-selected="handleMultiSelect"
      @change="handleMultiSelect">
    </cmdb-form-enummulti>

    <!-- list类型（单选） -->
    <bk-select
      v-else-if="property.bk_property_type === 'list'"
      ref="inputRef"
      :value="localValue"
      :placeholder="placeholder"
      @change="handleSelect"
      @selected="handleSelect">
      <bk-option
        v-for="option in listOptions"
        :key="option.id"
        :id="String(option.id)"
        :name="String(option.name)">
      </bk-option>
    </bk-select>

    <!-- 布尔类型 -->
    <bk-switcher
      v-else-if="property.bk_property_type === 'bool'"
      ref="inputRef"
      :value="localValue"
      @change="handleSwitchChange">
    </bk-switcher>

    <!-- 日期类型 -->
    <bk-date-picker
      v-else-if="property.bk_property_type === 'date'"
      ref="inputRef"
      :value="localValue"
      type="date"
      :placeholder="placeholder"
      @change="handleDateChange">
    </bk-date-picker>

    <!-- 时间类型 -->
    <bk-date-picker
      v-else-if="property.bk_property_type === 'time'"
      ref="inputRef"
      :value="localValue"
      type="datetime"
      :placeholder="placeholder"
      @change="handleDateChange">
    </bk-date-picker>

    <!-- 默认文本输入 -->
    <bk-input
      v-else
      ref="inputRef"
      type="text"
      :value="localValue"
      :placeholder="placeholder"
      @input="handleInput"
      @blur="handleBlurAndValidate">
    </bk-input>

    <!-- 错误提示 -->
    <span v-if="errorMessage" class="form-error">
      {{ errorMessage }}
    </span>
  </div>
</template>

<script>
import CmdbFormEnum from '../ui/form/enum.vue'
import CmdbFormEnummulti from '../ui/form/enummulti.vue'
import { parseOption, charLength, getMaxCharsByType } from '@/utils/validate-utils'

export default {
  name: 'PropertyFormElement',
  components: {
    CmdbFormEnum,
    CmdbFormEnummulti
  },
  props: {
    property: {
      type: Object,
      required: true
    },
    value: {
      type: [String, Number, Boolean, Array, Object],
      default: ''
    }
  },
  data() {
    return {
      localValue: '',
      errorMessage: ''
    }
  },
  computed: {
    isTextType() {
      return ['singlechar', 'varchar'].includes(this.property.bk_property_type)
    },
    isNumberType() {
      return ['int', 'float'].includes(this.property.bk_property_type)
    },
    // 计算最大字符数(用于 maxlength 属性)
    // 与 bk-input 内置计数器的计算方式保持一致(按字符数)
    maxCharLength() {
      const maxChars = getMaxCharsByType(this.property.bk_property_type)
      if (maxChars === null) return undefined
      return maxChars
    },
    placeholder() {
      return this.property.placeholder || `请输入${this.property.bk_property_name}`
    },
    listOptions() {
      const option = this.property.option
      
      if (!option) {
        return []
      }
      
      let parsedOption = option
      
      // 解析字符串格式
      if (typeof parsedOption === 'string') {
        try {
          parsedOption = JSON.parse(parsedOption)
        } catch (e) {
          return []
        }
      }
      
      // list类型的option格式通常是简单的字符串数组
      if (Array.isArray(parsedOption)) {
        return parsedOption.map(opt => {
          if (typeof opt === 'string' || typeof opt === 'number') {
            return { id: String(opt), name: String(opt) }
          }
          return null
        }).filter(item => item && item.id)
      }
      
      return []
    }
  },
  watch: {
    value: {
      immediate: true,
      handler(val) {
        this.localValue = val === null || val === undefined ? '' : val
      }
    }
  },
  methods: {
    handleInput(value) {
      this.localValue = value
      this.$emit('input', value)
    },
    handleBlurAndValidate() {
      this.validate()
      this.$emit('blur', this.localValue)
    },
    handleSelect(value) {
      this.localValue = value
      this.$emit('input', value)
      this.$emit('selected', value)
      this.$emit('change', value)
    },
    handleMultiSelect(value) {
      this.localValue = value
      this.$emit('input', value)
      this.$emit('change', value)
    },
    handleSwitchChange(value) {
      this.localValue = value
      this.$emit('input', value)
      this.$emit('change', value)
    },
    handleDateChange(value) {
      this.localValue = value
      this.$emit('input', value)
      this.$emit('change', value)
    },
    validate() {
      this.errorMessage = ''
      
      const value = this.localValue
      const property = this.property
      const propertyType = property.bk_property_type
      
      // 必填校验
      if (property.isrequired && (value === undefined || value === null || value === '')) {
        this.errorMessage = `${property.bk_property_name}不能为空`
        return false
      }
      
      // 如果值为空，则不进行后续类型校验
      if (value === undefined || value === null || value === '') {
        return true
      }
      
      // int 类型校验
      if (propertyType === 'int') {
        const numValue = Number(value)
        
        if (!Number.isInteger(numValue)) {
          this.errorMessage = '请输入整数'
          return false
        }
        
        // 范围校验
        const parsedOption = parseOption(property.option)
        if (parsedOption) {
          const min = parsedOption.min !== undefined && parsedOption.min !== '' && parsedOption.min !== null ? Number(parsedOption.min) : null
          const max = parsedOption.max !== undefined && parsedOption.max !== '' && parsedOption.max !== null ? Number(parsedOption.max) : null
          
          if (min !== null && numValue < min) {
            this.errorMessage = `最小值为 ${min}`
            return false
          }
          if (max !== null && numValue > max) {
            this.errorMessage = `最大值为 ${max}`
            return false
          }
        }
      }
      
      // float 类型校验
      if (propertyType === 'float') {
        const numValue = parseFloat(value)
        
        if (isNaN(numValue)) {
          this.errorMessage = '请输入有效的数字'
          return false
        }
        
        // 范围校验
        const parsedOption = parseOption(property.option)
        if (parsedOption) {
          const min = parsedOption.min !== undefined && parsedOption.min !== '' && parsedOption.min !== null ? Number(parsedOption.min) : null
          const max = parsedOption.max !== undefined && parsedOption.max !== '' && parsedOption.max !== null ? Number(parsedOption.max) : null
          
          if (min !== null && numValue < min) {
            this.errorMessage = `最小值为 ${min}`
            return false
          }
          if (max !== null && numValue > max) {
            this.errorMessage = `最大值为 ${max}`
            return false
          }
        }
      }
      
      // 字符串正则校验 + 字符长度校验(与 bk-input 计数器保持一致)
      if (['singlechar', 'longchar'].includes(propertyType)) {
        const maxChars = getMaxCharsByType(propertyType)
        const count = charLength(value)
        if (maxChars !== null && count > maxChars) {
          this.errorMessage = `请输入${maxChars}个字符以内的内容`
          return false
        }
        const parsedOption = parseOption(property.option)
        if (parsedOption && typeof parsedOption === 'string') {
          try {
            const regex = new RegExp(parsedOption)
            if (!regex.test(value)) {
              this.errorMessage = '格式不正确'
              return false
            }
          } catch (e) {}
        }
      }
      
      return true
    },
    clearError() {
      this.errorMessage = ''
    },
    focus() {
      this.$nextTick(() => {
        const input = this.$refs.inputRef?.focus
        if (input) {
          input()
        }
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.property-form-element {
  width: 100%;
  
  :deep(.bk-input) {
    width: 100%;
  }
  
  :deep(.bk-select) {
    width: 100%;
  }
  
  :deep(.bk-date-picker) {
    width: 100%;
  }
  
  :deep(.bk-switcher) {
    margin-top: 4px;
  }
  
  .form-error {
    display: block;
    margin-top: 4px;
    font-size: 12px;
    color: #ff5656;
  }
}
</style>
