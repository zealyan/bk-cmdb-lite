<template>
  <bk-input
    v-model.trim="localValue"
    v-bind="$attrs"
    type="textarea"
    @clear="() => $emit('clear')">
  </bk-input>
</template>

<script>
export default {
  name: 'cmdb-search-longchar',
  props: {
    value: {
      type: [String],
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
