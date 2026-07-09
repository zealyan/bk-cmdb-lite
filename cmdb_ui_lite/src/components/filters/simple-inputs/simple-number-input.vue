<template>
  <bk-input
    type="number"
    :model-value="modelValue"
    :placeholder="placeholder"
    @change="handleChange">
  </bk-input>
</template>

<script>
export default {
  name: 'SimpleNumberInput',
  props: {
    modelValue: {
      type: [Number, String],
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