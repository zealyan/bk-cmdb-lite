<template>
  <bk-time-picker
    v-model="localValue"
    :placeholder="placeholder">
  </bk-time-picker>
</template>

<script>
export default {
  name: 'SimpleTimePicker',
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
