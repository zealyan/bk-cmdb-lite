<template>
  <bk-datetime-picker
    v-model="localValue"
    :placeholder="placeholder">
  </bk-datetime-picker>
</template>

<script>
export default {
  name: 'SimpleDateTimePicker',
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
