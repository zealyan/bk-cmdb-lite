<template>
  <bk-time-picker
    :model-value="modelValue"
    :placeholder="placeholder"
    @change="handleChange">
  </bk-time-picker>
</template>

<script>
export default {
  name: 'SimpleTimePicker',
  props: {
    modelValue: {
      type: String,
      default: ''
    },
    placeholder: {
      type: String,
      default: ''
    }
  },
  methods: {
    handleChange(value) {
      this.$emit('update:modelValue', value)
      this.$emit('change', value)
    }
  }
}
</script>