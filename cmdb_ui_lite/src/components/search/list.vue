<template>
  <div class="g-expand">
    <bk-select
      searchable
      v-model="localValue"
      v-bind="$attrs"
      @clear="() => $emit('clear')">
      <bk-option v-for="option in normalizedOptions"
        :key="option.id"
        :id="option.id"
        :name="option.name">
      </bk-option>
    </bk-select>
  </div>
</template>

<script>
export default {
  name: 'cmdb-search-list',
  props: {
    value: {
      type: String,
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
    normalizedOptions() {
      if (!this.options || !this.options.length) {
        return []
      }
      if (typeof this.options[0] === 'string') {
        return this.options.map(opt => ({ id: opt, name: opt }))
      }
      if (typeof this.options[0] === 'object' && this.options[0] !== null) {
        return this.options.map(opt => ({
          id: opt.id !== undefined ? opt.id : opt,
          name: opt.name !== undefined ? opt.name : opt
        }))
      }
      return []
    },
    localValue: {
      get() {
        return this.value || ''
      },
      set(value) {
        this.$emit('input', value)
        this.$emit('change', value)
      }
    }
  }
}
</script>
