<template>
  <bk-select class="form-enum-selector"
      v-model="selected"
      :clearable="allowClear"
      :searchable="true"
      :disabled="disabled"
      :multiple="multiple"
      :placeholder="placeholder"
      :font-size="fontSize"
      :popover-options="{
        boundary: 'window'
      }"
      v-bind="$attrs"
      ref="selector"
      @toggle="handleToggle">
      <bk-option
        v-for="option in parsedOptions"
        :key="option.id"
        :id="option.id"
        :name="option.name">
      </bk-option>
    </bk-select>
</template>

<script>
export default {
  name: 'cmdb-form-enum',
  props: {
    value: {
      type: [Array, String, Number],
      default: ''
    },
    disabled: {
      type: Boolean,
      default: false
    },
    multiple: {
      type: Boolean,
      default: false
    },
    allowClear: {
      type: Boolean,
      default: false
    },
    autoSelect: {
      type: Boolean,
      default: true
    },
    options: {
      type: Array,
      default() {
        return []
      }
    },
    placeholder: {
      type: String,
      default: ''
    },
    fontSize: {
      type: [String, Number],
      default: 'medium'
    },
    property: {
      type: Object,
      default: () => ({})
    }
  },
  computed: {
    // 兼容原来通过property传递选项的方式
    parsedOptions() {
      if (this.options && this.options.length > 0) {
        return this.options
      }
      const option = this.property?.option
      if (!option) {
        return []
      }
      
      let parsedOption = option
      
      if (typeof option === 'string') {
        try {
          parsedOption = JSON.parse(option)
        } catch (e) {
          return []
        }
      }
      
      if (Array.isArray(parsedOption)) {
        return parsedOption.map(opt => {
          if (typeof opt === 'string') {
            return { id: opt, name: opt, type: 'text', is_default: false }
          }
          return {
            id: opt.id !== undefined ? opt.id : opt,
            name: opt.name !== undefined ? opt.name : opt,
            type: opt.type || 'text',
            is_default: opt.is_default || false
          }
        })
      }
      
      return []
    },
    selected: {
      get() {
        if (this.isEmpty(this.value)) {
          return this.getDefaultValue()
        }
        return this.value
      },
      set(value) {
        let emitValue = value
        if (value === '') {
          emitValue = this.multiple ? [] : null
        }
        this.$emit('input', emitValue)
        this.$emit('on-selected', emitValue)
      }
    }
  },
  watch: {
    value: {
      immediate: true,
      handler() {
        this.checkSelected()
      }
    }
  },
  methods: {
    isEmpty(value) {
      return ['', undefined, null].includes(value)
    },
    getDefaultValue() {
      if (this.autoSelect) {
        const defaultOption = this.parsedOptions.find(option => option.is_default)
        if (!defaultOption) return ''
        if (this.multiple) return [defaultOption.id]
        return defaultOption.id
      }
      return this.multiple ? [] : ''
    },
    checkSelected() {
      const { selected } = this
      if (this.value !== selected) {
        this.selected = selected
      }
    },
    focus() {
      this.$refs.selector.show()
    },
    handleToggle() {
      // do nothing
    }
  }
}
</script>

<style lang="scss" scoped>
  .form-enum-selector {
    width: 100%;
  }
</style>
