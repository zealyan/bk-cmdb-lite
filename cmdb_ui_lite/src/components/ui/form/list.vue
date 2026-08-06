<template>
  <bk-select
    class="form-list-selector"
    v-model="localValue"
    :disabled="disabled || readonly"
    :clearable="true"
    :searchable="true"
    @change="handleChange">
    <bk-option
      v-for="option in options"
      :key="option.id"
      :id="option.id"
      :name="option.name">
    </bk-option>
  </bk-select>
</template>

<script>
export default {
  name: 'cmdb-form-list',
  props: {
    value: {
      default: ''
    },
    property: {
      type: Object,
      default: () => ({})
    },
    disabled: Boolean,
    readonly: Boolean
  },
  data() {
    return {
      localValue: ''
    }
  },
  computed: {
    options() {
      const option = this.property?.option
      if (!option) {
        return []
      }
      let parsedOption = option
      
      if (typeof parsedOption === 'string') {
        try {
          parsedOption = JSON.parse(parsedOption)
        } catch (e) {}
      }
      
      if (Array.isArray(parsedOption)) {
        return parsedOption.map(opt => {
          if (typeof opt === 'object' && opt.id && opt.name) {
            return opt
          }
          return {
            id: opt,
            name: opt
          }
        })
      }
      
      return []
    }
  },
  watch: {
    value: {
      immediate: true,
      handler(val) {
        this.localValue = val || ''
      }
    }
  },
  methods: {
    handleChange(val) {
      this.$emit('input', val)
    }
  }
}
</script>

<style lang="scss" scoped>
.form-list-selector {
  width: 100%;
}
</style>
