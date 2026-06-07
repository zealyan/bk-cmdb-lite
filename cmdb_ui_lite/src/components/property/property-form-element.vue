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

    <!-- 枚举类型（单选） -->
    <cmdb-form-enum
      v-else-if="property.bk_property_type === 'enum'"
      ref="inputRef"
      :value="localValue"
      :property="property"
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
      @blur="handleBlur">
    </bk-input>
  </div>
</template>

<script>
import CmdbFormEnum from '../ui/form/enum.vue'
import CmdbFormEnummulti from '../ui/form/enummulti.vue'

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
    handleMultiSelect(value) {
      console.log('[handleMultiSelect]', value)
      this.localValue = value
      this.$emit('input', value)
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
}
</style>
