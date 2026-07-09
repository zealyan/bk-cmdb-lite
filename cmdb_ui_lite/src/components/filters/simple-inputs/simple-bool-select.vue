<template>
  <bk-select
    :model-value="modelValue"
    :options="options"
    :placeholder="placeholder"
    @change="handleChange">
  </bk-select>
</template>

<script>
export default {
  name: 'SimpleBoolSelect',
  props: {
    modelValue: {
      type: [Boolean, String],
      default: ''
    },
    placeholder: {
      type: String,
      default: ''
    }
  },
  computed: {
    options() {
      return [
        { label: '是', value: true },
        { label: '否', value: false }
      ]
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