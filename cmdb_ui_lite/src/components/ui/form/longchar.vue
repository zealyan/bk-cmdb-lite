<template>
  <bk-input
    v-model="localValue"
    type="textarea"
    :placeholder="placeholder"
    :disabled="disabled || readonly"
    :rows="rows"
    @input="handleInput"
    @change="handleChange">
  </bk-input>
</template>

<script>
export default {
  name: 'cmdb-form-longchar',
  props: {
    value: {
      default: ''
    },
    property: {
      type: Object,
      default: () => ({})
    },
    disabled: Boolean,
    readonly: Boolean,
    rows: {
      type: Number,
      default: 3
    }
  },
  data() {
    return {
      localValue: ''
    }
  },
  computed: {
    placeholder() {
      return this.property.placeholder || `请输入${this.property.bk_property_name || ''}`
    }
  },
  watch: {
    value: {
      immediate: true,
      handler(val) {
        this.localValue = val
      }
    }
  },
  methods: {
    handleInput(val) {
      this.$emit('input', val)
    },
    handleChange(val) {
      this.$emit('input', val)
    }
  }
}
</script>
