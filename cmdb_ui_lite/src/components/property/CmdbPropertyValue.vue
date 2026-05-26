<template>
  <span class="cmdb-property-value" :title="isShowOverflowTips ? displayValue : undefined">
    {{ displayValue }}
  </span>
</template>

<script>
export default {
  name: 'CmdbPropertyValue',

  props: {
    value: {
      type: [String, Number, Boolean, Array, Object],
      default: null
    },
    property: {
      type: Object,
      default: () => ({})
    },
    instance: {
      type: Object,
      default: () => ({})
    },
    isShowOverflowTips: {
      type: Boolean,
      default: true
    }
  },

  computed: {
    displayValue() {
      const { value } = this

      if (value === null || value === undefined || value === '') {
        return '-'
      }

      const propertyType = this.property?.bk_property_type || ''

      switch (propertyType) {
        case 'enum':
          return this.formatEnum(value)
        case 'bool':
          return this.formatBool(value)
        case 'list':
          return this.formatList(value)
        case 'float':
        case 'int':
          return String(value)
        default:
          return this.formatDefault(value)
      }
    }
  },

  methods: {
    getCopyValue() {
      const { value } = this
      if (value === null || value === undefined || value === '') {
        return ''
      }
      return String(this.displayValue)
    },

    formatEnum(value) {
      if (typeof value === 'number' || typeof value === 'string') {
        const option = this.property?.option
        if (option && typeof option === 'object') {
          return option[value] || String(value)
        }
      }
      return String(value)
    },

    formatBool(value) {
      if (typeof value === 'boolean') {
        return value ? '是' : '否'
      }
      if (typeof value === 'string') {
        const lowerValue = value.toLowerCase()
        if (lowerValue === 'true' || lowerValue === '1') return '是'
        if (lowerValue === 'false' || lowerValue === '0') return '否'
      }
      return String(value)
    },

    formatList(value) {
      if (Array.isArray(value)) {
        return value.join(', ')
      }
      if (typeof value === 'string') {
        try {
          const parsed = JSON.parse(value)
          if (Array.isArray(parsed)) {
            return parsed.join(', ')
          }
        } catch (e) {
          // ignore
        }
      }
      return String(value)
    },

    formatDefault(value) {
      if (typeof value === 'object') {
        return JSON.stringify(value)
      }
      return String(value)
    }
  }
}
</script>

<style lang="scss" scoped>
.cmdb-property-value {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
