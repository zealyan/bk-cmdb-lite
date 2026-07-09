<template>
  <div :class="['topology-tree-node', { 'is-selected': node.selected }]">
    <!-- 节点图标 -->
    <div
      :class="['node-icon', {
        'is-selected': node.selected,
        'is-template': isTemplate,
        'is-internal': isInternal
      }]">
      <!-- 空闲机池/故障机池图标 -->
      <i v-if="data.default !== 0 && data.default !== undefined" :class="internalNodeClass"></i>
      <!-- 普通节点图标（显示首字） -->
      <span v-else>{{ data.icon_text || data.bk_obj_name?.[0] || 'N' }}</span>
    </div>

    <!-- 节点名称 -->
    <span class="node-name" :title="node.name">{{ node.name }}</span>

    <!-- 节点额外信息（数量） - 使用loading组件包裹统计数据 -->
    <div class="node-extra">
      <cmdb-loading :class="['node-count', { 'is-selected': node.selected }]"
        :loading="['pending', undefined].includes(data.status)">
        {{ getNodeCount(data) }}
      </cmdb-loading>
    </div>
  </div>
</template>

<script>
import CmdbLoading from '@/components/loading/loading.vue'

export default {
  name: 'TopologyTreeNode',
  components: {
    CmdbLoading
  },
  props: {
    node: {
      type: Object,
      default: () => ({})
    },
    data: {
      type: Object,
      default: () => ({})
    },
    nodeCountType: {
      type: String,
      default: 'host_count'
    }
  },
  computed: {
    // 内部节点（空闲机池、故障机池）的图标类名
    internalNodeClass() {
      const iconMap = {
        1: 'icon-cc-host-free-pool',
        2: 'icon-cc-host-breakdown',
        default: 'icon-cc-host-free-pool'
      }
      return iconMap[this.data.default] || iconMap.default
    },
    // 是否是内部节点（空闲机池、故障机池）
    isInternal() {
      return this.data.default !== 0 && this.data.default !== undefined
    },
    // 是否是模板创建的节点
    isTemplate() {
      return this.data.service_template_id || this.data.set_template_id
    }
  },
  methods: {
    // 获取节点数量（与原项目保持一致）
    getNodeCount(data) {
      const count = data[this.nodeCountType]
      if (typeof count === 'number') {
        return count
      }
      return 0
    }
  }
}
</script>

<style lang="scss" scoped>
.topology-tree-node {
  display: flex;
  width: 100%;
  cursor: pointer;

  &:hover {
    .node-count {
      background-color: #e1ecff;
    }
  }

  &.is-selected {
    .node-icon {
      background-color: #3a84ff;
      &.is-internal {
        color: #3a84ff;
      }
    }
    .node-name {
      color: #3a84ff;
    }
    .node-count {
      background-color: #a2c5fd;
      color: #fff;
    }
  }

  .node-icon {
    display: flex;
    flex: none;
    width: 20px;
    height: 20px;
    line-height: 20px;
    align-items: center;
    justify-content: center;
    margin: 8px 4px 8px 0;
    border-radius: 50%;
    background-color: #c4c6cc;
    font-size: 12px;
    font-style: normal;
    color: #fff;

    &.is-template {
      background-color: #97aed6;
    }

    &.is-selected {
      background-color: #3a84ff;
      &.is-internal {
        color: #3a84ff;
      }
    }

    &.is-internal {
      font-size: 14px;
      color: #63656e;
      background-color: transparent;
    }

    &:hover {
      background-color: #3a84ff;
    }
  }

  .node-name {
    display: block;
    flex: 1;
    height: 36px;
    line-height: 36px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #63656e;
  }

  .node-extra {
    margin-left: auto;
    display: flex;

    .node-count {
      padding: 0 5px;
      margin: 9px 20px 9px 4px;
      height: 18px;
      line-height: 17px;
      border-radius: 2px;
      background-color: #f0f1f5;
      color: #979ba5;
      font-size: 12px;
      text-align: center;
      &.is-selected {
        background-color: #a2c5fd;
        color: #fff;
      }
      &.loading {
        background-color: transparent;
      }
    }
  }
}
</style>