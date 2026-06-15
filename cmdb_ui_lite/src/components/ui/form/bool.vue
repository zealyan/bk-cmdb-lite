<template>
  <bk-switcher
    class="form-bool"
    size="small"
    theme="primary"
    v-model="localValue"
    :disabled="disabled || readonly">
  </bk-switcher>
</template>

<script>
export default {
  name: 'cmdb-form-bool',
  props: {
    value: {
      type: [String, Boolean, Number],
      default: false
    },
    property: {
      type: Object,
      default: () => ({})
    },
    disabled: Boolean,
    readonly: Boolean
  },
  computed: {
    localValue: {
      get() {
        if (typeof this.value === 'boolean') {
          return this.value
        }
        if (typeof this.value === 'string') {
          return this.value === 'true'
        }
        if (typeof this.value === 'number') {
          return Boolean(this.value)
        }
        return false
      },
      set(value) {
        this.$emit('input', value)
        this.$emit('change', value)
      }
    }
  }
}
</script>

<style lang="scss" scoped>
  .form-bool {
    display: inline-block;
    vertical-align: middle;
  }
</style>
