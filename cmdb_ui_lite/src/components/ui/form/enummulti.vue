<template>
  <div class="g-expand">
    <bk-select class="form-enummulti-selector"
      v-model="selected"
      :clearable="allowClear"
      :searchable="true"
      :disabled="disabled"
      display-tag
      selected-style="checkbox"
      :multiple="localMultiple"
      :placeholder="placeholder"
      :font-size="fontSize"
      :popover-options="{
        boundary: 'window'
      }"
      v-bind="$attrs"
      ref="selector"
      @toggle="handleToggle">
      <bk-option
        v-for="(option, index) in parsedOptions"
        :key="index"
        :id="option.id"
        :name="option.name">
      </bk-option>
    </bk-select>
  </div>
</template>

<script>
import isEqual from 'lodash/isEqual'

function isEmptyPropertyValue(value) {
  return value === null || value === undefined || value === '' || (Array.isArray(value) && value.length === 0)
}

export default {
  name: 'cmdb-form-enummulti',
  props: {
    value: {
      type: [Array, String],
      default() {
        return []
      }
    },
    disabled: {
      type: Boolean,
      default: false
    },
    multiple: {
      type: Boolean,
      default: true
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
  data() {
    return {
      initValue: this.value
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
    localMultiple() {
      if (Array.isArray(this.initValue) && this.initValue.length > 1 && !this.multiple) {
        return true
      }
      return this.multiple
    },
    selected: {
      get() {
        if (isEmptyPropertyValue(this.value)) {
          return this.getDefaultValue()
        }

        if (!this.localMultiple) {
          return Array.isArray(this.value) ? this.value[0] : this.value
        }

        let vals
        if (!Array.isArray(this.value)) {
          try {
            vals = JSON.parse(this.value)
            if (!Array.isArray(vals)) {
              vals = [this.value]
            }
          } catch (e) {
            vals = [this.value]
          }
        } else {
          vals = this.value
        }

        return vals.filter(val => this.parsedOptions?.some?.(option => option.id === val))
      },
      set(value) {
        this.$emit('input', value)
        this.$emit('on-selected', value)
        this.$emit('change', value)
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
      return !value?.length
    },
    getDefaultValue() {
      if (this.autoSelect) {
        const defaultOptions = (this.parsedOptions || []).filter(option => option.is_default)
        const defaultValue = defaultOptions.map(option => option.id)
        return this.localMultiple ? defaultValue : defaultValue[0]
      }

      return this.localMultiple ? [] : ''
    },
    checkSelected() {
      const { selected } = this
      if (!isEqual(this.value, selected)) {
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
  .form-enummulti-selector {
    width: 100%;
  }
</style>
