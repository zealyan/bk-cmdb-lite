<template>
  <div class="tree-layout">
    <bk-input
      class="tree-search"
      clearable
      right-icon="bk-icon icon-search"
      placeholder="请输入关键词"
      v-model.trim="filterKeyword"
      @input="handleFilter">
    </bk-input>
    <bk-big-tree
      ref="tree"
      class="topology-tree"
      selectable
      display-matched-node-descendants
      :height="treeHeight"
      :node-height="36"
      :options="{
        idKey: getNodeId,
        nameKey: 'bk_inst_name',
        childrenKey: 'child'
      }"
      :default-expand-all="true"
      @select-change="handleSelectChange"
      @expand-change="handleExpandChange">
      <template #default="{ node, data }">
        <topology-tree-node
          :node="node"
          :data="data"
          :node-count-type="nodeCountType">
        </topology-tree-node>
      </template>
    </bk-big-tree>
  </div>
</template>

<script>
import TopologyTreeNode from './topology-tree-node.vue'

// 模拟业务拓扑数据（业务 -> 集群 -> 模块）
const mockTopologyData = [
  {
    bk_obj_id: 'biz',
    bk_obj_name: '业务',
    bk_inst_id: 1,
    bk_inst_name: '蓝鲸平台',
    icon_text: '业',
    host_count: 256,
    service_instance_count: 128,
    default: 0,
    child: [
      {
        bk_obj_id: 'set',
        bk_obj_name: '集群',
        bk_inst_id: 10,
        bk_inst_name: '空闲机池',
        icon_text: '集',
        host_count: 15,
        service_instance_count: 0,
        default: 1,
        is_idle_set: true,
        child: [
          {
            bk_obj_id: 'module',
            bk_obj_name: '模块',
            bk_inst_id: 101,
            bk_inst_name: '空闲机',
            icon_text: '模',
            host_count: 15,
            service_instance_count: 0,
            default: 1,
            child: []
          },
          {
            bk_obj_id: 'module',
            bk_obj_name: '模块',
            bk_inst_id: 102,
            bk_inst_name: '故障机',
            icon_text: '模',
            host_count: 0,
            service_instance_count: 0,
            default: 2,
            child: []
          }
        ]
      },
      {
        bk_obj_id: 'set',
        bk_obj_name: '集群',
        bk_inst_id: 11,
        bk_inst_name: '正式环境',
        icon_text: '集',
        host_count: 180,
        service_instance_count: 90,
        default: 0,
        child: [
          {
            bk_obj_id: 'module',
            bk_obj_name: '模块',
            bk_inst_id: 111,
            bk_inst_name: '应用服务',
            icon_text: '模',
            host_count: 80,
            service_instance_count: 40,
            default: 0,
            child: []
          },
          {
            bk_obj_id: 'module',
            bk_obj_name: '模块',
            bk_inst_id: 112,
            bk_inst_name: '数据服务',
            icon_text: '模',
            host_count: 50,
            service_instance_count: 25,
            default: 0,
            child: []
          },
          {
            bk_obj_id: 'module',
            bk_obj_name: '模块',
            bk_inst_id: 113,
            bk_inst_name: '网关服务',
            icon_text: '模',
            host_count: 30,
            service_instance_count: 15,
            default: 0,
            child: []
          },
          {
            bk_obj_id: 'module',
            bk_obj_name: '模块',
            bk_inst_id: 114,
            bk_inst_name: '监控服务',
            icon_text: '模',
            host_count: 20,
            service_instance_count: 10,
            default: 0,
            child: []
          }
        ]
      },
      {
        bk_obj_id: 'set',
        bk_obj_name: '集群',
        bk_inst_id: 12,
        bk_inst_name: '测试环境',
        icon_text: '集',
        host_count: 40,
        service_instance_count: 20,
        default: 0,
        child: [
          {
            bk_obj_id: 'module',
            bk_obj_name: '模块',
            bk_inst_id: 121,
            bk_inst_name: '测试服务',
            icon_text: '模',
            host_count: 25,
            service_instance_count: 12,
            default: 0,
            child: []
          },
          {
            bk_obj_id: 'module',
            bk_obj_name: '模块',
            bk_inst_id: 122,
            bk_inst_name: '开发服务',
            icon_text: '模',
            host_count: 15,
            service_instance_count: 8,
            default: 0,
            child: []
          }
        ]
      },
      {
        bk_obj_id: 'set',
        bk_obj_name: '集群',
        bk_inst_id: 13,
        bk_inst_name: '预发布环境',
        icon_text: '集',
        host_count: 21,
        service_instance_count: 18,
        default: 0,
        child: [
          {
            bk_obj_id: 'module',
            bk_obj_name: '模块',
            bk_inst_id: 131,
            bk_inst_name: '预发布服务',
            icon_text: '模',
            host_count: 21,
            service_instance_count: 18,
            default: 0,
            child: []
          }
        ]
      }
    ]
  },
  {
    bk_obj_id: 'biz',
    bk_obj_name: '业务',
    bk_inst_id: 2,
    bk_inst_name: '配置平台',
    icon_text: '业',
    host_count: 128,
    service_instance_count: 64,
    default: 0,
    child: [
      {
        bk_obj_id: 'set',
        bk_obj_name: '集群',
        bk_inst_id: 20,
        bk_inst_name: '空闲机池',
        icon_text: '集',
        host_count: 8,
        service_instance_count: 0,
        default: 1,
        is_idle_set: true,
        child: [
          {
            bk_obj_id: 'module',
            bk_obj_name: '模块',
            bk_inst_id: 201,
            bk_inst_name: '空闲机',
            icon_text: '模',
            host_count: 8,
            service_instance_count: 0,
            default: 1,
            child: []
          }
        ]
      },
      {
        bk_obj_id: 'set',
        bk_obj_name: '集群',
        bk_inst_id: 21,
        bk_inst_name: '生产环境',
        icon_text: '集',
        host_count: 100,
        service_instance_count: 50,
        default: 0,
        child: [
          {
            bk_obj_id: 'module',
            bk_obj_name: '模块',
            bk_inst_id: 211,
            bk_inst_name: '核心服务',
            icon_text: '模',
            host_count: 60,
            service_instance_count: 30,
            default: 0,
            child: []
          },
          {
            bk_obj_id: 'module',
            bk_obj_name: '模块',
            bk_inst_id: 212,
            bk_inst_name: '辅助服务',
            icon_text: '模',
            host_count: 40,
            service_instance_count: 20,
            default: 0,
            child: []
          }
        ]
      },
      {
        bk_obj_id: 'set',
        bk_obj_name: '集群',
        bk_inst_id: 22,
        bk_inst_name: '开发环境',
        icon_text: '集',
        host_count: 20,
        service_instance_count: 14,
        default: 0,
        child: [
          {
            bk_obj_id: 'module',
            bk_obj_name: '模块',
            bk_inst_id: 221,
            bk_inst_name: '开发测试',
            icon_text: '模',
            host_count: 20,
            service_instance_count: 14,
            default: 0,
            child: []
          }
        ]
      }
    ]
  }
]

export default {
  name: 'TopologyTree',
  components: {
    TopologyTreeNode
  },
  props: {
    active: {
      type: String,
      default: 'hostList'
    }
  },
  data() {
    return {
      filterKeyword: '',
      nodeCountType: 'host_count',
      treeHeight: 600,
      topologyData: mockTopologyData
    }
  },
  watch: {
    active: {
      immediate: true,
      handler(value) {
        const map = {
          hostList: 'host_count',
          serviceInstance: 'service_instance_count',
          nodeInfo: 'host_count'
        }
        if (Object.keys(map).includes(value)) {
          this.nodeCountType = map[value]
        }
      }
    }
  },
  mounted() {
    this.initTopology()
    this.updateTreeHeight()
    window.addEventListener('resize', this.updateTreeHeight)
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.updateTreeHeight)
  },
  methods: {
    // 初始化拓扑树
    initTopology() {
      this.$refs.tree.setData(this.topologyData)
      this.$nextTick(() => {
        this.setDefaultState()
      })
    },
    // 设置默认选中节点
    setDefaultState() {
      const [firstNode] = this.$refs.tree.nodes
      if (firstNode) {
        this.$refs.tree.setExpanded(firstNode.id)
        this.$refs.tree.setSelected(firstNode.id, { emitEvent: true })
      }
    },
    // 生成节点ID
    getNodeId(data) {
      return `${data.bk_obj_id}-${data.bk_inst_id}`
    },
    // 处理搜索过滤
    handleFilter() {
      if (this.filterKeyword) {
        this.$refs.tree.filter(this.filterKeyword)
      } else {
        this.$refs.tree.filter('')
      }
    },
    // 处理节点选择变化
    handleSelectChange(node) {
      this.$emit('node-select', node)
    },
    // 处理节点展开变化
    handleExpandChange(node) {
      // 展开节点时可以做一些额外处理
    },
    // 更新树高度
    updateTreeHeight() {
      const container = this.$el.parentElement
      if (container) {
        this.treeHeight = container.clientHeight - 60
      }
    },
    // 获取当前选中的节点
    getSelectedNode() {
      return this.$refs.tree.selectedNode
    }
  }
}
</script>

<style lang="scss" scoped>
.tree-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.tree-search {
  display: block;
  width: auto;
  margin: 0 20px;
  flex-shrink: 0;
}

.topology-tree {
  flex: 1;
  padding: 10px 0;
  margin-right: 2px;
  overflow: auto;

  &::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }

  &::-webkit-scrollbar-thumb {
    border-radius: 20px;
    background: rgba(165, 165, 165, 0.3);
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }
}
</style>