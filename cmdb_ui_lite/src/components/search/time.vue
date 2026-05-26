<template>
  <bk-date-picker
    type="datetimerange"
    transfer
    :value="localValue"
    v-bind="$attrs"
    format="yyyy-MM-dd HH:mm:ss"
    @clear="() => $emit('clear')"
    @change="handleChange">
  </bk-date-picker>
</template>

<script>
export default {
  name: 'cmdb-search-time',
  props: {
    value: {
      type: Array,
      default: () => ([])
    },
    property: {
      type: Object,
      default: () => ({})
    }
  },
  computed: {
    localValue: {
      get() {
        return [...this.value]
      },
      set(values) {
        this.$emit('input', values)
        this.$emit('change', values)
      }
    }
  },
  methods: {
    handleChange(values) {
      if (values.toString() === this.value.toString()) return
      this.localValue = values.filter(value => !!value)
    }
  }
}
</script>
