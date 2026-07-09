<template>
  <bk-select
    :model-value="modelValue"
    :options="options"
    :multiple="multiple"
    :placeholder="placeholder"
    @change="handleChange">
  </bk-select>
</template>

<script>
export default {
  name: 'SimpleEnumSelect',
  props: {
    modelValue: {
      type: [String, Array],
      default: ''
    },
    placeholder: {
      type: String,
      default: ''
    },
    property: {
      type: Object,
      default: () => ({})
    }
  },
  computed: {
    multiple() {
      return this.property.ismultiple || this.property.bk_property_type === 'enummulti'
    },
    options() {
      try {
        const option = this.property.option
        if (!option) return []
        const parsed = typeof option === 'string' ? JSON.parse(option) : option
        if (Array.isArray(parsed)) {
          return parsed.map(item => ({
            label: item.name || item.id,
            value: item.id || item.name
          }))
        }
      } catch (e) {
        console.error('Parse enum option failed:', e)
      }
      return []
    }
  },
  methods: {
    handleChange(value) {
      this.$emit('update:modelValue', value)
      this.$emit('change', value)
    }
  }
}
</script>