<template>
  <div class="property-form-element">
    <!-- 文本输入框 -->
    <bk-input
      v-if="isTextType"
      ref="inputRef"
      type="text"
      :value="localValue"
      :placeholder="placeholder"
      @input="handleInput"
      @blur="handleBlur">
    </bk-input>

    <!-- 文本域 -->
    <bk-input
      v-else-if="property.bk_property_type === 'longchar'"
      ref="inputRef"
      type="textarea"
      :value="localValue"
      :placeholder="placeholder"
      :rows="3"
      @input="handleInput"
      @blur="handleBlur">
    </bk-input>

    <!-- 整数/浮点数 -->
    <bk-input
      v-else-if="isNumberType"
      ref="inputRef"
      type="number"
      :value="localValue"
      :placeholder="placeholder"
      @input="handleInput"
      @blur="handleBlur">
    </bk-input>

    <!-- 枚举类型 -->
    <bk-select
      v-else-if="property.bk_property_type === 'enum'"
      ref="inputRef"
      :value="localValue"
      :placeholder="placeholder"
      @change="handleSelect"
      @selected="handleSelect">
      <bk-option
        v-for="option in enumOptions"
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
      @blur="handleBlur">
    </bk-input>
  </div>
</template>

<script>
export default {
  name: 'PropertyFormElement',
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
      localValue: ''
    }
  },
  computed: {
    isTextType() {
      return ['singlechar', 'varchar'].includes(this.property.bk_property_type)
    },
    isNumberType() {
      return ['int', 'float'].includes(this.property.bk_property_type)
    },
    enumOptions() {
      const option = this.property.option || this.property.bk_property_option
      
      if (!option) {
        console.log('[enumOptions] No option found for property:', this.property.bk_property_id)
        return []
      }
      
      console.log('[enumOptions] Raw option:', { option, type: typeof option })
      
      let parsedOption = option
      
      // 解析字符串格式
      if (typeof parsedOption === 'string') {
        try {
          parsedOption = JSON.parse(parsedOption)
          console.log('[enumOptions] Parsed option:', parsedOption)
        } catch (e) {
          console.error('[enumOptions] JSON parse error:', e)
          return []
        }
      }
      
      let result = []
      
      try {
        // 如果是对象格式 { "key1": "name1", "key2": "name2" }
        if (parsedOption && typeof parsedOption === 'object' && !Array.isArray(parsedOption)) {
          result = Object.entries(parsedOption).map(([key, name]) => ({
            id: String(key),
            name: String(name)
          }))
        }
        // 数组格式 [{ id: "1", name: "选项1" }] 或 ["a", "b"]
        else if (Array.isArray(parsedOption)) {
          result = parsedOption.map(item => {
            if (typeof item === 'string' || typeof item === 'number') {
              return { id: String(item), name: String(item) }
            }
            if (item && typeof item === 'object') {
              const id = item.id || item.key || item.value
              const name = item.name || item.label || item.text || id
              if (id) {
                return { id: String(id), name: String(name || id) }
              }
            }
            return null
          }).filter(item => item && item.id)
        }
        
        console.log('[enumOptions] Processed result:', result)
      } catch (e) {
        console.error('[enumOptions] processing error:', e)
        return []
      }
      
      return result
    },
    placeholder() {
      return this.property.placeholder || `请输入${this.property.bk_property_name}`
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
    handleBlur() {
      this.$emit('blur', this.localValue)
    },
    handleSelect(value) {
      console.log('[handleSelect]', value)
      this.localValue = value
      this.$emit('input', value)
      this.$emit('selected', value)
      this.$emit('change', value)
    },
    handleSwitchChange(value) {
      this.localValue = value
      this.$emit('change', value)
    },
    handleDateChange(value) {
      console.log('[handleDateChange]', value)
      this.localValue = value
      this.$emit('input', value)
      this.$emit('change', value)
    },
    focus() {
      this.$nextTick(() => {
        const input = this.$refs.inputRef?.$refs?.input
        if (input) {
          input.focus()
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
}
</style>
