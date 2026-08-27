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

    <!-- 节点额外信息 -->
    <div class="node-extra">
      <!-- 新建按钮 - hover时显示，替代数量标签 -->
      <span v-if="isShowCreate" class="node-create-trigger">
        <bk-button class="node-button"
          theme="primary"
          @click.stop="handleCreate(node)">
          新建
        </bk-button>
      </span>

      <!-- 数量标签 - 默认显示，hover时隐藏 -->
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
    },
    // 该节点在主线中的直接子层模型ID（由父组件按主线顺序计算）。
    // 为空表示其为最底层（如 module），不显示新建按钮；非空则显示，
    // 从而对任意主线顺序（biz→appsys→zone→set→module）都正确开放"新建"。
    childModelId: {
      type: String,
      default: ''
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
    },
    // 是否显示新建按钮：仅当该节点在主线中存在直接子层（childModelId 非空）。
    // 替代原写死的 biz/set 判断，使 appsys/zone 等自定义层也能在其父节点下新建，
    // 且 module（最底层）因 childModelId 为空自动隐藏按钮。
    // 空闲机池（is_idle_set）为内置特殊集群，禁止在其下新建模块（对齐原项目：
    // 空闲机池/故障机池由系统维护，用户不可在业务拓扑手动新建子节点）。
    isShowCreate() {
      return !!this.childModelId && !this.data.is_idle_set
    }
  },
  methods: {
    // 获取节点数量
    // 注：「数量大于 999 显示为 999+」的逻辑已撤销，以下为原始实现（原始数字直接返回），
    // 999+ 截断逻辑保留注释以备参考：
    //   return count > 999 ? '999+' : count
    getNodeCount(data) {
      const count = data[this.nodeCountType]
      if (typeof count === 'number') {
        return count
        // return count > 999 ? '999+' : count
      }
      return 0
    },
    // 点击新建按钮，向父组件传递 create 事件
    handleCreate(node) {
      this.$emit('create', node)
    }
  }
}
</script>

<style lang="scss" scoped>
.topology-tree-node {
  display: flex;
  width: 100%;
  cursor: pointer;

  // hover时：显示新建按钮，隐藏数量标签
  &:hover {
    .node-extra {
      .node-create-trigger {
        display: inline-block;
        & ~ .node-count {
          display: none;
        }
      }
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

    // 新建按钮触发器 - 默认隐藏，hover时显示
    .node-create-trigger {
      display: none;
      font-size: 0;

      .node-button {
        height: 24px;
        padding: 0 6px;
        margin: 0 20px 0 4px;
        line-height: 22px;
        border-radius: 4px;
        font-size: 12px;
        min-width: auto;
      }
    }

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
