<template>
  <bk-date-picker class="cmdb-date"
    v-bind="otherAttrs"
    v-model="date"
    transfer
    editable
    :clearable="clearable"
    :placeholder="placeholder"
    :disabled="disabled || readonly">
  </bk-date-picker>
</template>

<script>
function formatTime(originalTime, format = 'YYYY-MM-DD HH:mm:ss') {
  if (!originalTime) {
    return ''
  }
  try {
    const date = new Date(originalTime)
    if (isNaN(date.getTime())) {
      return originalTime
    }
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    
    if (format === 'YYYY-MM-DD') {
      return `${year}-${month}-${day}`
    }
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  } catch (e) {
    return originalTime
  }
}

export default {
  name: 'cmdb-form-date',
  props: {
    value: {
      type: String,
      default: ''
    },
    property: {
      type: Object,
      default: () => ({})
    },
    disabled: {
      type: Boolean,
      default: false
    },
    readonly: {
      type: Boolean,
      default: false
    },
    clearable: {
      type: Boolean,
      default: true
    }
  },
  computed: {
    placeholder() {
      return this.property.placeholder || '选择日期'
    },
    date: {
      get() {
        if (!this.value) {
          return ''
        }
        return new Date(this.value)
      },
      set(value) {
        const previousValue = this.value
        const currentValue = formatTime(value, 'YYYY-MM-DD')
        this.$emit('input', currentValue)
        if (currentValue !== previousValue) {
          this.$emit('change', currentValue, previousValue)
        }
      }
    },
    otherAttrs() {
      const { options, ...otherAttrs } = this.$attrs
      return otherAttrs
    }
  }
}
</script>

<style lang="scss" scoped>
.cmdb-date {
  width: 100%;

  &[size="small"] {
    ::v-deep {
      .bk-date-picker-rel {
        .icon-wrapper {
          height: 26px;
          line-height: 26px;
        }
        .bk-date-picker-editor {
          height: 26px;
          line-height: 26px;
        }
      }
    }
  }
  :deep(.bk-date-picker-editor) {
    &:focus {
      border-color: #3a84ff !important;
    }
  }
}
</style>
