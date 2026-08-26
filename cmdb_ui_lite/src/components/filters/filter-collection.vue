<template>
  <bk-select class="filter-collection"
    ref="selector"
    searchable
    :popover-width="220"
    font-size="normal"
    v-bk-tooltips="'已收藏的条件'"
    @click.native="loadCollections">
    <icon-button slot="trigger"
      class="filter-trigger"
      icon="icon-cc-star"
      :class="{ 'is-selected': !!storageCollection }"
      @click="loadCollections">
    </icon-button>
    <bk-option v-for="collection in collections"
      :key="collection.id"
      :id="collection.id"
      :name="collection.name"
      @click.native="handleApply(collection)">
      <div class="collection-item">
        <i class="collection-state bk-icon icon-check-1" v-if="storageCollection && storageCollection.id === collection.id"></i>
        <span class="collection-name">{{collection.name}}</span>
        <span class="collection-options">
          <i class="option-icon option-edit icon-cc-edit" @click.stop="handleEdit(collection)"></i>
          <i class="option-icon option-delete bk-icon icon-close" @click.stop="handleRemove(collection)"></i>
        </span>
      </div>
    </bk-option>
    <div class="business-extension" slot="extension">
      <a href="javascript:void(0)" class="extension-link" @click="handleCreate">
        <i class="bk-icon icon-plus-circle"></i>
        新增收藏条件
      </a>
    </div>
  </bk-select>
</template>

<script>
import IconButton from '@/components/ui/button/icon-button.vue'
import FilterStore from './store'

// 用户级「条件筛选收藏」：
//  - 数据落在服务端 user_custom（config_key='filter_collection'，按登录用户隔离）。
//  - 以 FilterStore 为单一数据源（collections / activeCollection，及 load/setActive/create/remove/update），
//    与高级筛选的条件状态（selected / condition）天然同步：
//      · 应用收藏 → setActiveCollection 把条件同步回 selected/condition；
//      · 添加收藏 → createCollection 从 selected/condition 序列化当前条件。
export default {
  name: 'FilterCollection',
  components: {
    IconButton
  },
  data() {
    return {
    }
  },
  computed: {
    collections() {
      return FilterStore.collections || []
    },
    storageCollection() {
      return FilterStore.activeCollection
    }
  },
  methods: {
    async loadCollections() {
      await FilterStore.loadCollections()
      this.$nextTick(() => {
        this.$refs.selector && this.$refs.selector.show && this.$refs.selector.show()
      })
    },
    /**
     * 点击某条收藏 → 直接应用该收藏（不依赖 bk-select 的 change/value 数组）。
     * 直接传入 collection 对象，规避了本端口 bk-magic-vue 2.5.9 在 multiple 模式下
     * 切换选项时 value 数组计算异常（点了 B 却仍把 A 当作最新项）导致「二次点击不同步」的问题。
     * 当前激活态由 storageCollection 驱动（星标高亮 + 选项勾选）。
     */
    handleApply(collection) {
      FilterStore.setActiveCollection(collection)
      this.$emit('apply', collection)
    },
    handleEdit(collection) {
      const newName = prompt('编辑收藏条件名称', collection.name)
      if (newName && newName.trim()) {
        FilterStore.updateCollection({ id: collection.id, name: newName.trim() })
      }
    },
    handleRemove(collection) {
      FilterStore.removeCollection(collection)
    },
    handleCreate() {
      // 打开高级筛选抽屉，在其中通过「收藏此条件」保存当前条件（与上游一致）
      import('./filter-form.js').then(({ default: FilterFormApi }) => {
        FilterFormApi.show()
      }).catch(e => console.error('[FilterCollection] 打开高级筛选失败', e))
    }
  }
}
</script>

<style lang="scss" scoped>
.filter-collection {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  width: 32px;
  height: 32px;
  overflow: hidden;

  &.is-disabled {
    cursor: pointer;
  }

  ::v-deep {
    .bk-tooltip-ref {
      display: flex !important;
      align-items: center;
      justify-content: center;
    }
  }
}

.filter-trigger {
  color: #63656e;

  &:hover,
  &.is-selected {
    color: $primaryColor;
  }

  ::v-deep {
    .icon-wrapper:before {
      font-size: 18px;
    }
  }
}

.collection-item {
  display: flex;
  align-items: center;
  padding: 0 16px;
  margin: 0 -16px;

  &:hover {
    .collection-options {
      display: initial;
    }
  }

  .collection-state {
    font-size: 24px;
    margin-left: -14px;

    & ~ .collection-name {
      margin-left: initial;
    }
  }

  .collection-name {
    margin-left: -6px;
    @include ellipsis;
  }

  .collection-options {
    display: none;
    margin-right: -10px;
    margin-left: auto;

    .option-icon {
      width: 24px;
      height: 24px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: $textColor;

      &:hover {
        color: $primaryColor;
      }
    }

    .option-icon.option-edit {
      font-size: 12px;
    }

    .option-icon.option-delete {
      font-size: 22px;
    }
  }
}

.extension-link {
  display: block;
  line-height: 38px;
  padding: 0 9px;
  font-size: 13px;
  color: #63656E;

  &:hover {
    opacity: .85;
  }

  .bk-icon {
    font-size: 18px;
    color: #979BA5;
    vertical-align: text-top;
  }
}
</style>
