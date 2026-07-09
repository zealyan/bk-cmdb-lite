<template>
  <bk-input
    :model-value="modelValue"
    :placeholder="placeholder"
    @change="handleChange">
  </bk-input>
</template>

<script>
export default {
  name: 'SimpleTextInput',
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