<template>
  <div class="options-layout">
    <!-- 左侧操作按钮区 -->
    <div class="options options-left">
      <bk-button class="option" theme="primary"
        :disabled="!hasSelection"
        @click="handleMultipleEdit">
        编辑
      </bk-button>

      <bk-dropdown-menu
        class="option ml10" trigger="click"
        font-size="medium"
        :disabled="!hasSelection"
        @show="isTransferMenuOpen = true"
        @hide="isTransferMenuOpen = false">
        <bk-button slot="dropdown-trigger"
          :disabled="!hasSelection">
          <span>转移至</span>
          <i :class="['dropdown-icon bk-icon icon-angle-down',{ 'open': isTransferMenuOpen }]"></i>
        </bk-button>
        <ul class="bk-dropdown-list" slot="dropdown-content">
          <li class="bk-dropdown-item" @click="handleTransfer('idle')">空闲模块</li>
          <li class="bk-dropdown-item" @click="handleTransfer('business')">业务模块</li>
          <li :class="['bk-dropdown-item', { disabled: !isIdleSetModules }]"
            @click="handleTransfer('resource')">
            主机池
          </li>
          <li :class="['bk-dropdown-item', { disabled: !isIdleSetModules }]"
            @click="handleTransfer('acrossBusiness')">
            其他业务
          </li>
        </ul>
      </bk-dropdown-menu>

      <bk-button class="option ml10 refresh-btn" icon="bk-icon icon-refresh"
        @click="handleRefresh">
      </bk-button>
    </div>

    <!-- 右侧搜索区 -->
    <div class="options options-right">
      <filter-fast-search class="option-fast-search"
        @search="handleSearch">
      </filter-fast-search>
      <filter-collection class="option-collection ml10"
        @apply="handleCollectionApply">
      </filter-collection>
      <icon-button :class="['option-filter', 'ml10', { active: hasFilterCondition }]"
        icon="icon-cc-funnel"
        v-bk-tooltips.top="'高级筛选'"
        @click="handleSetFilters">
      </icon-button>
    </div>
  </div>
</template>

<script>
import FilterFastSearch from '@/components/filters/filter-fast-search.vue'
import FilterCollection from '@/components/filters/filter-collection.vue'
import IconButton from '@/components/ui/button/icon-button.vue'

export default {
  name: 'HostListOptions',
  components: {
    FilterFastSearch,
    FilterCollection,
    IconButton
  },
  props: {
    // 选中的主机数量
    selection: {
      type: Array,
      default: () => []
    },
    // 主机总数
    count: {
      type: Number,
      default: 0
    },
    // 当前选中的拓扑节点
    selectedNode: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      isTransferMenuOpen: false,
      isMoreMenuOpen: false,
      searchKeyword: '',
      hasFilterCondition: false
    }
  },
  computed: {
    hasSelection() {
      return !!this.selection.length
    },
    isNormalNode() {
      return this.selectedNode && this.selectedNode.data.default === 0
    },
    isNormalModuleNode() {
      return this.isNormalNode && this.selectedNode.data.bk_obj_id === 'module'
    },
    isIdleSetModules() {
      return this.selection.every(data =>
        data.module && data.module.every(module => module.default >= 1)
      )
    }
  },
  methods: {
    handleAddHost() {
      this.$emit('add-host')
    },
    handleMultipleEdit() {
      this.$emit('edit')
    },
    handleTransfer(type) {
      if (!this.hasSelection) return
      this.$emit('transfer', type)
    },
    handleExport() {
      if (!this.hasSelection) return
      this.$emit('export')
    },
    handleBatchExport() {
      if (!this.count) return
      this.$emit('batch-export')
    },
    handleRefresh() {
      this.$emit('refresh')
    },
    handleSearch(keyword) {
      this.searchKeyword = keyword
      this.$emit('search', keyword)
    },
    handleClearSearch() {
      this.searchKeyword = ''
      this.$emit('search', '')
    },
    handleSetFilters() {
      this.hasFilterCondition = true
      this.$emit('set-filters')
    },
    handleCollectionApply(collection) {
      this.$emit('collection-apply', collection)
    }
  }
}
</script>

<style lang="scss" scoped>
.options-layout {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  margin-top: 12px;
}

.options {
  display: flex;
  align-items: center;

  &.options-left {
    justify-content: flex-start;
  }

  &.options-right {
    flex: 1;
    justify-content: flex-end;
  }

  .option {
    display: inline-block;
    vertical-align: middle;
  }

  .option-fast-search {
    flex: 1;
    max-width: 300px;
    margin-left: 10px;
  }

  .option-collection,
  .option-filter {
    flex: 32px 0 0;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 32px;
    cursor: pointer;
    color: #63656e;
    border-radius: 2px;
    transition: color 0.2s;

    &:hover,
    &.active {
      color: $primaryColor;
    }
  }

  .option-filter {
    ::v-deep {
      .icon-wrapper {
        font-size: 0;

        &:before {
          font-size: 14px;
        }
      }
    }
  }

  .dropdown-icon {
    &.open {
      transform: rotate(180deg);
    }
  }

  // 刷新按钮（仅图标、无文字）：bk-button 默认图标字号偏大且偏下，
  // 1) 字号收敛到 14px，与同栏「高级筛选」漏斗图标保持一致；
  // 2) 按钮改为 flex 居中，让图标在水平/垂直方向均居中（修复略微偏下）
  .refresh-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;

    ::v-deep .bk-icon {
      font-size: 14px;
      line-height: 30;
    }
  }
}

.bk-dropdown-list {
  font-size: 14px;
  color: $textColor;

  .bk-dropdown-item {
    position: relative;
    display: block;
    padding: 0 20px;
    margin: 0;
    line-height: 32px;
    cursor: pointer;
    @include ellipsis;

    &:not(.disabled):hover {
      background-color: #EAF3FF;
      color: $primaryColor;
    }

    &.disabled {
      color: $textDisabledColor;
      cursor: not-allowed;
    }
  }
}
</style>
