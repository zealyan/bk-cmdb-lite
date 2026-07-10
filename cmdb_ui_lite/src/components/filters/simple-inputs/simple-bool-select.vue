<template>
  <bk-select
    v-model="localValue"
    :options="options"
    :placeholder="placeholder">
  </bk-select>
</template>

<script>
export default {
  name: 'SimpleBoolSelect',
  props: {
    value: {
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
    },
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
