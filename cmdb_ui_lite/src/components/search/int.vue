<template>
  <bk-input
    v-model.trim="localValue"
    v-bind="$attrs"
    type="number"
    @clear="() => $emit('clear')">
  </bk-input>
</template>

<script>
export default {
  name: 'cmdb-search-int',
  props: {
    value: {
      type: [Number, String],
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
        const numValue = value === '' ? '' : Number(value)
        this.$emit('input', numValue)
        this.$emit('change', numValue)
      }
    }
  }
}
</script>
