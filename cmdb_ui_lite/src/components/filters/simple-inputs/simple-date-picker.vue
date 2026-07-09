<template>
  <bk-date-picker
    :model-value="modelValue"
    :placeholder="placeholder"
    @change="handleChange">
  </bk-date-picker>
</template>

<script>
export default {
  name: 'SimpleDatePicker',
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