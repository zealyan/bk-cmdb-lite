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
        case 'enummulti':
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
      const option = this.property?.option
      if (!option) {
        return String(value)
      }

      // 解析 option
      let parsedOption = option
      if (typeof option === 'string') {
        try {
          parsedOption = JSON.parse(option)
        } catch (e) {
          return String(value)
        }
      }

      // 新格式: [{id: "xxx", name: "显示名", type: "text", is_default: false}]
      if (Array.isArray(parsedOption)) {
        // 支持多选枚举和多选枚举：value 可能是字符串或数组
        if (Array.isArray(value)) {
          // 多选枚举：返回多个选项名称
          const names = value.map(v => this.findEnumName(parsedOption, v)).filter(n => n)
          return names.join(', ') || String(value)
        } else {
          // 单选枚举
          const name = this.findEnumName(parsedOption, value)
          return name || String(value)
        }
      }

      // 旧格式: { "key1": "name1", "key2": "name2" }
      if (parsedOption && typeof parsedOption === 'object') {
        const name = parsedOption[value]
        return name || String(value)
      }

      return String(value)
    },

    findEnumName(options, value) {
      const optionItem = options.find(opt => opt.id === value || opt.id === String(value))
      return optionItem?.name
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
      // list 类型是单选，值是单个字符串，不需要解析
      if (value === null || value === undefined || value === '') {
        return '-'
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
