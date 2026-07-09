<template>
  <bk-datetime-picker
    :model-value="modelValue"
    :placeholder="placeholder"
    @change="handleChange">
  </bk-datetime-picker>
</template>

<script>
export default {
  name: 'SimpleDateTimePicker',
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