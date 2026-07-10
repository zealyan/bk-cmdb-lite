<template>
  <section class="filter-wrapper" v-if="selected.length || showIPTag">
    <label class="filter-label">
      <i class="label-icon icon-cc-funnel"></i>
      <span class="label-text">检索项</span>
      <span class="label-colon">:</span>
    </label>
    <div class="filter-list" ref="filterList">
      <filter-tag-ip v-if="showIPTag"></filter-tag-ip>
      <filter-tag-item
        v-for="property in selected"
        :key="property.bk_property_id"
        :property="property"
        v-bind="condition[property.bk_property_id]">
      </filter-tag-item>
      <bk-button class="filter-clear" text
        v-if="showClear"
        @click="handleResetAll">
        清空条件
      </bk-button>
    </div>
  </section>
</template>

<script>
import FilterTagIp from './filter-tag-ip.vue'
import FilterTagItem from './filter-tag-item.vue'
import FilterStore from './store'
import Utils from './utils'

export default {
  name: 'FilterTag',
  components: {
    FilterTagIp,
    FilterTagItem
  },
  computed: {
    condition() {
      return FilterStore.condition?.condition || {}
    },
    showIPTag() {
      const list = Utils.splitIP(FilterStore.IP.text)
      return !!list.length
    },
    selected() {
      return FilterStore.selected.filter((property) => {
        const cond = this.condition[property.bk_property_id]
        if (!cond) return false
        const { value } = cond
        return value !== null && value !== undefined && !!value.toString().length
      })
    },
    showClear() {
      const count = this.selected.length + (this.showIPTag ? 1 : 0)
      return count > 1
    }
  },
  watch: {
    selected() {
      if (!(this.selected.length || this.showIPTag)) {
        FilterStore.setActiveCollection && FilterStore.setActiveCollection(null)
      }
    }
  },
  methods: {
    handleResetAll() {
      FilterStore.resetAll()
      FilterStore.setActiveCollection && FilterStore.setActiveCollection(null)
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