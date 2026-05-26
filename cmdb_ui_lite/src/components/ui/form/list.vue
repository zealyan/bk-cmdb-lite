<template>
  <bk-select
    v-model="localValue"
    :disabled="disabled || readonly"
    :clearable="true"
    :searchable="true"
    @change="handleChange">
    <bk-option
      v-for="option in options"
      :key="option.id"
      :id="option.id"
      :name="option.name">
    </bk-option>
  </bk-select>
</template>

<script>
export default {
  name: 'cmdb-form-list',
  props: {
    value: {
      default: ''
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
      localValue: ''
    }
  },
  computed: {
    options() {
      const option = this.property?.option
      if (!option) {
        return []
      }
      if (Array.isArray(option)) {
        return option
      }
      if (typeof option === 'string') {
        try {
          return JSON.parse(option)
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
        this.localValue = val
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
