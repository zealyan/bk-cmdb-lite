<template>
  <bk-member-selector
    v-model="localValue"
    :disabled="disabled || readonly"
    @change="handleChange">
  </bk-member-selector>
</template>

<script>
export default {
  name: 'cmdb-form-user',
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
