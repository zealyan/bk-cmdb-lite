<template>
  <bk-select
    v-model="localValue"
    :disabled="disabled || readonly"
    :clearable="true"
    :searchable="options.length > 5"
    multiple
    @change="handleChange">
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
  name: 'cmdb-form-enummulti',
  props: {
    value: {
      default: () => []
    },
    property: {
      type: Object,
      default: () => ({})
    },
    disabled: Boolean,
    readonly: Boolean
  },
  data() {
    return {
      localValue: []
    }
  },
  computed: {
    parsedOptions() {
      const option = this.property?.option
      if (!option) {
        return []
      }
      if (Array.isArray(option)) {
        return option.map(opt => ({
          id: typeof opt === 'string' ? opt : opt.id,
          name: typeof opt === 'string' ? opt : opt.name
        }))
      }
      if (typeof option === 'string') {
        try {
          return JSON.parse(option).map(opt => ({
            id: typeof opt === 'string' ? opt : opt.id,
            name: typeof opt === 'string' ? opt : opt.name
          }))
        } catch (e) {
          return option.split(',').map(opt => ({
            id: opt.trim(),
            name: opt.trim()
          }))
        }
      }
      return []
    }
  },
  watch: {
    value: {
      immediate: true,
      handler(val) {
        this.localValue = Array.isArray(val) ? val : []
      }
    }
  },
  methods: {
    handleChange(val) {
      this.$emit('input', val)
    }
  }
}
</script>
