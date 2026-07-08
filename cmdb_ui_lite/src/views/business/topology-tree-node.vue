<script>
export default {
  name: 'TopologyTreeNode',
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
    nodeIconClass() {
      // 内部节点（空闲机池等）
      if (this.data.default !== 0 && this.data.default !== undefined) {
        const iconMap = {
          1: 'icon-cc-host-free-pool',
          2: 'icon-cc-host-breakdown',
          default: 'icon-cc-host-free-pool'
        }
        return iconMap[this.data.default] || iconMap.default
      }
      return ''
    },
    isInternal() {
      return this.data.default !== 0 && this.data.default !== undefined
    },
    isSelected() {
      return this.node.selected || false
    },
    nodeCount() {
      const count = this.data[this.nodeCountType]
      if (typeof count === 'number') {
        return count
      }
      return 0
    },
    iconText() {
      if (this.data.icon_text) {
        return this.data.icon_text
      }
      // 根据对象类型显示图标文字
      const objName = this.data.bk_obj_name || ''
      return objName[0] || ''
    },
    nodeIconTips() {
      // 根据节点类型显示提示
      const objId = this.data.bk_obj_id
      const tipsMap = {
        biz: '业务',
        set: '集群',
        module: '模块'
      }
      return tipsMap[objId] || this.data.bk_obj_name || ''
    }
  }
}
</script>

<template>
  <div :class="['topology-tree-node', { 'is-selected': isSelected }]">
    <div
      :class="['node-icon', {
        'is-selected': isSelected,
        'is-internal': isInternal
      }]">
      <i v-if="isInternal" :class="nodeIconClass"></i>
      <span v-else>{{ iconText }}</span>
    </div>

    <span class="node-name" :title="node.name">{{ node.name }}</span>

    <div class="node-extra">
      <span :class="['node-count', { 'is-selected': isSelected }]">
        {{ nodeCount }}
      </span>
    </div>
  </div>
</template>

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

    &.is-internal {
      font-size: 14px;
      color: #63656e;
      background-color: transparent;
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
    }
  }
}
</style>