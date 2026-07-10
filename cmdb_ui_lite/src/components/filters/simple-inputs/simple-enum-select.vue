<template>
  <bk-select
    v-model="localValue"
    :options="options"
    :multiple="multiple"
    :placeholder="placeholder">
  </bk-select>
</template>

<script>
export default {
  name: 'SimpleEnumSelect',
  props: {
    value: {
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
    },
    localValue: {
      get() {
        return this.value
      },
      set(val) {
        this.$emit('input', val)
        this.$emit('change', val)
      }
    }
  }
}
</script>
