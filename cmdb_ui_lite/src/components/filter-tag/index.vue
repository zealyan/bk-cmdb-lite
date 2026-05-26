<template>
  <section class="filter-wrapper" v-if="hasCondition">
    <label class="filter-label">
      <i class="label-icon bk-icon icon-cc-funnel"></i>
      <span class="label-text">检索项</span>
      <span class="label-colon">:</span>
    </label>
    <div class="filter-list">
      <FilterTagItem
        v-for="tag in visibleTags"
        :key="tag.id"
        :property="tag.property"
        :operator="tag.operator"
        :value="tag.value"
        :propertyName="tag.propertyName"
        @remove="handleRemoveTag(tag)">
      </FilterTagItem>
      <bk-button
        v-if="showClearButton"
        class="filter-clear"
        text
        @click="handleClearAll">
        清空条件
      </bk-button>
    </div>
  </section>
</template>

<script>
import FilterTagItem from './filter-tag-item.vue'

export default {
  name: 'FilterTag',
  components: {
    FilterTagItem
  },
  props: {
    filterTags: {
      type: Array,
      default: () => []
    }
  },
  computed: {
    visibleTags() {
      return this.filterTags.filter(tag => {
        const value = tag.value
        if (Array.isArray(value)) {
          return value.length > 0
        }
        return value !== null && value !== undefined && String(value).length > 0
      })
    },
    hasCondition() {
      return this.visibleTags.length > 0
    },
    showClearButton() {
      return this.visibleTags.length > 0
    }
  },
  methods: {
    handleRemoveTag(tag) {
      this.$emit('remove', tag)
    },
    handleClearAll() {
      this.$emit('clear-all')
    }
  }
}
</script>

<style lang="scss" scoped>
.filter-wrapper {
  display: flex;
  margin: 10px 0 0 0;

  .filter-label {
    display: flex;
    font-size: 12px;
    align-items: center;
    align-self: flex-start;
    line-height: 22px;

    .label-icon {
      color: #979BA5;
    }

    .label-text {
      margin-left: 4px;
    }

    .label-colon {
      margin: 0 5px;
    }
  }

  .filter-list {
    display: flex;
    flex-wrap: wrap;
    flex: 1;
  }

  .filter-clear {
    line-height: initial;
    margin: 0 0 10px 10px;
    font-size: 12px;
  }
}
</style>
