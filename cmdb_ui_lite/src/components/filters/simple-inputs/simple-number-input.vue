<template>
  <bk-input
    type="number"
    v-model="localValue"
    :placeholder="placeholder">
  </bk-input>
</template>

<script>
export default {
  name: 'SimpleNumberInput',
  props: {
    value: {
      type: [Number, String],
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
