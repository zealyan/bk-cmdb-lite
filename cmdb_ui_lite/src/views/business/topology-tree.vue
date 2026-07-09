<template>
  <section class="tree-layout" v-bkloading="{ isLoading: loading, opacity: 1 }">
    <bk-input class="tree-search"
      clearable
      right-icon="bk-icon icon-search"
      placeholder="请输入关键词"
      v-model.trim="filterKeyword"
      @input="handleFilter">
    </bk-input>
    <bk-big-tree ref="tree" class="topology-tree"
      selectable
      display-matched-node-descendants
      :height="treeHeight"
      :node-height="36"
      :options="{
        idKey: getNodeId,
        nameKey: 'bk_inst_name',
        childrenKey: 'child'
      }"
      :data="treeData"
      @select-change="handleSelectChange"
      @expand-change="handleExpandChange">
      <template #default="{ node, data }">
        <topology-tree-node
          :node="node"
          :data="data"
          :node-count-type="nodeCountType">
        </topology-tree-node>
      </template>
      <template #empty>
        <div class="tree-empty">
          <bk-exception type="empty" scene="part">
            <div>暂无业务数据</div>
          </bk-exception>
        </div>
      </template>
    </bk-big-tree>
  </section>
</template>

<script>
import TopologyTreeNode from './topology-tree-node.vue'
import { topoAPI } from '@/api/topo'
import RouterQuery from '@/utils/router-query'

const MODEL_INFO = {
  biz: { bk_obj_name: '业务', icon_text: '业' },
  set: { bk_obj_name: '集群', icon_text: '集' },
  module: { bk_obj_name: '模块', icon_text: '模' }
}

export default {
  name: 'TopologyTree',
  components: {
    TopologyTreeNode
  },
  props: {
    active: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      filterKeyword: RouterQuery.get('keyword', ''),
      nodeCountType: 'host_count',
      treeHeight: 600,
      treeData: [],
      loading: false,
      loadedNodes: new Set(),
      initialized: false,
      bizId: null
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
    },
    filterKeyword(value) {
      RouterQuery.set('keyword', value)
    }
  },
  created() {
  },
  async mounted() {
    await this.initTopology()
    this.updateTreeHeight()
    window.addEventListener('resize', this.updateTreeHeight)
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.updateTreeHeight)
    this.destroyWatcher()
  },
  methods: {
    async initTopology() {
      this.loading = true
      try {
        const topology = await this.getInstanceTopology()

        this.treeData = topology
        this.$refs.tree.setData(this.treeData)
        
        this.$nextTick(() => {
          this.setDefaultState()
          this.createWatcher()
          this.setNodeCount(this.$refs.tree?.nodes || [])
        })
      } catch (e) {
        console.error('加载拓扑树失败:', e)
        this.treeData = []
      } finally {
        this.loading = false
      }
    },

    async getInstanceTopology() {
      const bizId = this.getCurrentBizId()
      this.bizId = bizId

      const res = await topoAPI.getInstanceTopo(bizId, { with_statistics: true })
      const data = res.data || {}

      if (!data.bk_inst_id) {
        return []
      }

      const info = MODEL_INFO.biz
      return [{
        ...data,
        ...info,
        bk_obj_id: 'biz',
        bk_inst_id: data.bk_inst_id,
        bk_inst_name: data.bk_inst_name,
        default: data.default || 0,
        host_count: data.count || 0,
        expanded: true,
        child: (data.child || []).map(set => ({
          ...set,
          ...MODEL_INFO.set,
          bk_obj_id: 'set',
          bk_inst_id: set.bk_inst_id,
          bk_inst_name: set.bk_inst_name,
          default: set.default || 0,
          bk_biz_id: bizId,
          host_count: set.count || 0,
          child: (set.child || []).map(mod => ({
            ...mod,
            ...MODEL_INFO.module,
            bk_obj_id: 'module',
            bk_inst_id: mod.bk_inst_id,
            bk_inst_name: mod.bk_inst_name,
            default: mod.default || 0,
            bk_set_id: set.bk_inst_id,
            bk_biz_id: bizId,
            host_count: mod.count || 0,
            child: []
          }))
        }))
      }]
    },

    getCurrentBizId() {
      const queryBizId = RouterQuery.get('bk_biz_id')
      if (queryBizId) {
        return parseInt(queryBizId, 10)
      }
      return 2
    },

    createWatcher() {
      this.nodeUnwatch = RouterQuery.watch('node', this.handleNodeChange)
      this.filterUnwatch = RouterQuery.watch('keyword', (value) => {
        this.filterKeyword = value
      })
    },

    handleNodeChange(newNodeId) {
      if (!newNodeId) return
      const node = this.$refs.tree?.getNodeById(newNodeId)
      if (node) {
        this.expandToNode(node)
        if (!node.selected) {
          this.$refs.tree.setSelected(node.id, { emitEvent: true })
        }
        this.handleDefaultExpand(node)
      }
    },

    destroyWatcher() {
      this.nodeUnwatch && this.nodeUnwatch()
      this.filterUnwatch && this.filterUnwatch()
    },

    setDefaultState() {
      const queryNodeId = RouterQuery.get('node', '')
      if (queryNodeId) {
        const node = this.$refs.tree?.getNodeById(queryNodeId)
        if (node) {
          this.expandToNode(node)
          this.$refs.tree.setSelected(node.id, { emitEvent: true })
          this.handleDefaultExpand(node)
          return
        }
      }

      const firstNode = this.$refs.tree?.nodes?.[0]
      if (firstNode) {
        this.$refs.tree.setExpanded(firstNode.id)
        this.$refs.tree.setSelected(firstNode.id, { emitEvent: true })
        this.handleDefaultExpand(firstNode)
      }
    },

    expandToNode(node) {
      const path = []
      let current = node
      while (current) {
        path.unshift(current)
        current = current.parent
      }
      path.forEach(n => {
        this.$refs.tree.setExpanded(n.id)
      })
    },

    handleDefaultExpand(node) {
      const nodes = []
      let parentNode = node
      while (parentNode) {
        nodes.push(...parentNode.children)
        if (!parentNode.parent) {
          nodes.push(parentNode)
        }
        parentNode = parentNode.parent
      }
      this.setNodeCount(nodes)
    },

    async setNodeCount(nodes) {
      if (!nodes || !Array.isArray(nodes) || !nodes.length) return

      const normalNodes = nodes.filter(n => n.data && ['biz', 'set', 'module'].includes(n.data.bk_obj_id))
      if (!normalNodes.length) return

      normalNodes.forEach(({ data }) => this.$set(data, 'status', 'pending'))

      try {
        const condition = normalNodes.map(({ data }) => ({
          bk_obj_id: data.bk_obj_id,
          bk_inst_id: data.bk_inst_id,
          bk_biz_id: data.bk_biz_id || this.bizId
        }))

        const response = await topoAPI.getTopoStatistics(this.bizId, { condition })
        const results = response.data || []

        normalNodes.forEach(({ data }) => {
          const count = results.find(r =>
            r.bk_obj_id === data.bk_obj_id && r.bk_inst_id === data.bk_inst_id
          )
          this.$set(data, 'status', 'finished')
          this.$set(data, 'host_count', count?.host_count || 0)
          this.$set(data, 'service_instance_count', count?.service_instance_count || 0)
        })
      } catch (error) {
        console.error('获取统计数据失败:', error)
        normalNodes.forEach((node) => {
          this.$set(node.data, 'status', 'error')
        })
      }
    },

    getNodeId(data) {
      return `${data.bk_obj_id}-${data.bk_inst_id}`
    },

    handleFilter() {
      if (this.filterKeyword) {
        this.$refs.tree.filter(this.filterKeyword)
        this.$nextTick(() => {
          this.setNodeCount(this.$refs.tree.visibleNodes)
        })
      } else {
        this.$refs.tree.filter('')
      }
    },

    handleSelectChange(node) {
      const oldId = RouterQuery.get('node')
      const newId = node.id

      RouterQuery.set({
        node: newId,
        page: 1,
        _t: Date.now()
      })

      if (oldId !== newId) {
        this.$emit('node-select', node)
      }
    },

    handleExpandChange(node) {
      if (!node.expanded) return
      this.setNodeCount([node, ...node.children])
    },

    updateTreeHeight() {
      const container = this.$el.parentElement
      if (container) {
        this.treeHeight = container.clientHeight - 60
      }
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

.tree-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}
</style>