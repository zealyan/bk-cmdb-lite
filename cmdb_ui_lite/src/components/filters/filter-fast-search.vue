<template>
  <bk-input class="filter-fast-search"
    v-model.trim="value"
    placeholder="请输入IP或固资编号"
    @enter="handleSearch"
    @clear="handleSearch">
  </bk-input>
</template>

<script>
export default {
  name: 'FilterFastSearch',
  data() {
    return {
      value: ''
    }
  },
  methods: {
    handleSearch() {
      this.$emit('search', this.value)
    }
  }
}
</script>

<style lang="scss" scoped>
.filter-fast-search {
  display: inline-flex;
}
</style>
