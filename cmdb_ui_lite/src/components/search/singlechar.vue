<template>
  <bk-input
    v-model.trim="localValue"
    v-bind="$attrs"
    @clear="() => $emit('clear')">
  </bk-input>
</template>

<script>
export default {
  name: 'cmdb-search-singlechar',
  props: {
    value: {
      type: [String, Number],
      default: ''
    },
    property: {
      type: Object,
      default: () => ({})
    }
  },
  computed: {
    localValue: {
      get() {
        return this.value
      },
      set(value) {
        this.$emit('input', value)
        this.$emit('change', value)
      }
    }
  }
}
</script>
