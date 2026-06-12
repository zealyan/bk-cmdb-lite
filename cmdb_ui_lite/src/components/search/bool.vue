<template>
  <bk-select
    v-model="localValue"
    :placeholder="placeholder"
    searchable
    size="small"
    @change="handleChange">
    <bk-option id="true" name="是(true)"></bk-option>
    <bk-option id="false" name="否(false)"></bk-option>
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
    options: {
      type: Array,
      default: () => []
    },
    property: {
      type: Object,
      default: () => ({})
    },
    placeholder: {
      type: String,
      default: '请选择'
    },
    size: {
      type: String,
      default: 'small'
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
