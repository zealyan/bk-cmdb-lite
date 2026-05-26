<template>
  <bk-select
    searchable
    v-model="localValue"
    v-bind="$attrs"
    @change="handleChange"
    @clear="() => $emit('clear')">
    <bk-option
      v-for="option in options"
      :key="option"
      :id="option"
      :name="option">
    </bk-option>
  </bk-select>
</template>

<script>
export default {
  name: 'cmdb-search-timezone',
  props: {
    value: {
      type: [String, Array],
      default: ''
    },
    options: {
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
        return this.value
      },
      set(value) {
        this.$emit('input', value)
        this.$emit('change', value)
      }
    }
  },
  methods: {
    handleChange(value) {
      this.$emit('input', value)
      this.$emit('change', value)
    }
  }
}
</script>
