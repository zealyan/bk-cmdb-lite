<template>
  <bk-select class="filter-collection"
    ref="selector"
    searchable
    multiple
    :popover-width="220"
    font-size="normal"
    v-model="selected"
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
      :name="collection.name">
      <div class="collection-item">
        <i class="collection-state bk-icon icon-check-1" v-if="selected.includes(collection.id)"></i>
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

export default {
  name: 'FilterCollection',
  components: {
    IconButton
  },
  data() {
    return {
      collections: [],
      selected: [],
      storageCollection: null,
      loadingCollections: false
    }
  },
  methods: {
    async loadCollections() {
      if (this.loadingCollections) return
      this.loadingCollections = true
      try {
        // 简化版：从本地存储加载收藏条件
        const stored = localStorage.getItem('cmdb_filter_collections')
        this.collections = stored ? JSON.parse(stored) : []
        this.$nextTick(() => {
          this.$refs.selector && this.$refs.selector.show && this.$refs.selector.show()
        })
      } catch (e) {
        console.error(e)
      } finally {
        this.loadingCollections = false
      }
    },
    handleApply(value) {
      const selectedId = Array.isArray(value) && value.length > 0 ? value[value.length - 1] : null
      this.storageCollection = this.collections.find(c => c.id === selectedId) || null
      this.$emit('apply', this.storageCollection)
    },
    handleEdit(collection) {
      const newName = prompt('编辑收藏条件名称', collection.name)
      if (newName && newName.trim()) {
        collection.name = newName.trim()
        this.saveCollections()
      }
    },
    handleRemove(collection) {
      this.collections = this.collections.filter(c => c.id !== collection.id)
      this.saveCollections()
    },
    handleCreate() {
      const name = prompt('请输入收藏条件名称')
      if (name && name.trim()) {
        this.collections.push({
          id: Date.now(),
          name: name.trim()
        })
        this.saveCollections()
      }
    },
    saveCollections() {
      localStorage.setItem('cmdb_filter_collections', JSON.stringify(this.collections))
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
