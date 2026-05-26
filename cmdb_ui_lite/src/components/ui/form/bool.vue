<template>
  <bk-switcher
    v-model="localValue"
    :disabled="disabled || readonly"
    @change="handleChange">
  </bk-switcher>
</template>

<script>
export default {
  name: 'cmdb-form-bool',
  props: {
    value: {
      default: false
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
      localValue: false
    }
  },
  watch: {
    value: {
      immediate: true,
      handler(val) {
        this.localValue = Boolean(val)
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
