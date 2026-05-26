<template>
  <bk-select
    v-model="localValue"
    v-bind="$attrs"
    @change="handleChange"
    @clear="() => $emit('clear')">
    <bk-option id="true" name="true"></bk-option>
    <bk-option id="false" name="false"></bk-option>
  </bk-select>
</template>

<script>
export default {
  name: 'cmdb-search-bool',
  props: {
    value: {
      type: [String, Boolean],
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
        if (this.value === true || this.value === 'true') {
          return 'true'
        } else if (this.value === false || this.value === 'false') {
          return 'false'
        }
        return ''
      },
      set(value) {
        const realValue = value === 'true'
        this.$emit('input', realValue)
        this.$emit('change', realValue)
      }
    }
  },
  methods: {
    handleChange(value) {
      const realValue = value === 'true'
      this.$emit('input', realValue)
      this.$emit('change', realValue)
    }
  }
}
</script>
