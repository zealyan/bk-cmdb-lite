<template>
  <bk-input
    v-model="localValue"
    :placeholder="placeholder">
  </bk-input>
</template>

<script>
export default {
  name: 'SimpleTextInput',
  props: {
    value: {
      type: String,
      default: ''
    },
    placeholder: {
      type: String,
      default: ''
    }
  },
  computed: {
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
