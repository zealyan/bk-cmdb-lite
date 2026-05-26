<template>
  <div class="g-expand">
    <bk-select
      multiple
      display-tag
      selected-style="checkbox"
      searchable
      v-model="localValue"
      v-bind="$attrs"
      :show-select-all="true"
      @clear="() => $emit('clear')">
      <bk-option v-for="(option, index) in options"
        :key="index"
        :id="option"
        :name="option">
      </bk-option>
    </bk-select>
  </div>
</template>

<script>
export default {
  name: 'cmdb-search-list',
  props: {
    value: {
      type: Array,
      default: () => ([])
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
        return this.value || []
      },
      set(value) {
        this.$emit('input', value)
        this.$emit('change', value)
      }
    }
  }
}
</script>
