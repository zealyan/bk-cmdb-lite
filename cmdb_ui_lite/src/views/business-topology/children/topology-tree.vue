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
      @select-change="handleSelectChange"
      @expand-change="handleExpandChange">
      <template #default="{ node, data }">
        <topology-tree-node
          :node="node"
          :data="data"
          :node-count-type="nodeCountType"
          @create="handleShowCreateDialog">
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

    <!-- 新建集群对话框 -->
    <bk-dialog class="bk-dialog-no-padding"
      v-model="createDialog.visible"
      :show-footer="false"
      :mask-close="false"
      :width="580"
      @cancel="handleCancelCreate">
      <create-set v-if="createDialog.visible"
        :parent-node="createDialog.parentNode"
        @submit="handleCreateSetSubmit"
        @cancel="handleCancelCreate">
      </create-set>
    </bk-dialog>
  </section>
</template>

<script>
import TopologyTreeNode from './topology-tree-node.vue'
import CreateSet from './create-set.vue'
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
    TopologyTreeNode,
    CreateSet
  },
  props: {
    active: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      filterKeyword: '',
      nodeCountType: 'host_count',
      treeHeight: 600,
      treeData: [],
      loading: false,
      loadedNodes: new Set(),
      initialized: false,
      bizId: null,
      isRestoringExpanded: false,
      createDialog: {
        visible: false,
        parentNode: null
      }
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
      if (RouterQuery.router) {
        RouterQuery.set('keyword', value)
      }
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
    this.saveExpandedState()
  },
  methods: {
    async initTopology() {
      console.log('[TopologyTree] initTopology: start')
      this.loading = true
      try {
        const topology = await this.getInstanceTopology()
        console.log('[TopologyTree] initTopology: topology data loaded, length:', topology.length)
        console.log('[TopologyTree] initTopology: first node:', topology[0] ? topology[0].bk_inst_name : 'null')

        this.treeData = topology
        this.$refs.tree.setData(this.treeData)
        console.log('[TopologyTree] initTopology: tree data set')

        await this.$nextTick()
        console.log('[TopologyTree] initTopology: nextTick 1 completed')
        console.log('[TopologyTree] initTopology: tree nodes:', this.$refs.tree?.nodes?.map(n => n.id))

        this.setDefaultStateDirectly()
        console.log('[TopologyTree] initTopology: default state set directly')

        this.createWatcher()
        console.log('[TopologyTree] initTopology: watcher created')
      } catch (e) {
        console.error('[TopologyTree] initTopology: error:', e)
        this.treeData = []
      } finally {
        this.loading = false
        console.log('[TopologyTree] initTopology: finished')
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
      const routeBizId = this.$route?.params?.bizId
      if (routeBizId) {
        return parseInt(routeBizId, 10)
      }
      return 2
    },

    createWatcher() {
      this.nodeUnwatch = RouterQuery.watch('node', this.setDefaultState, { immediate: true })
      this.filterUnwatch = RouterQuery.watch('keyword', (value) => {
        this.filterKeyword = value || ''
      })
    },

    destroyWatcher() {
      this.nodeUnwatch && this.nodeUnwatch()
      this.filterUnwatch && this.filterUnwatch()
    },

    setDefaultStateDirectly() {
      console.log('[TopologyTree] setDefaultStateDirectly: start')
      const queryNodeId = this.$route.query.node || ''
      const bizId = this.getCurrentBizId()
      const [firstNode] = this.$refs.tree?.nodes || []

      let defaultNode = null

      if (queryNodeId) {
        defaultNode = this.$refs.tree?.getNodeById(queryNodeId)
      }

      if (!defaultNode) {
        defaultNode = firstNode || this.$refs.tree?.getNodeById(`biz-${bizId}`)
      }

      if (defaultNode) {
        const { tree } = this.$refs

        console.log('[TopologyTree] setDefaultStateDirectly: defaultNode data:', JSON.stringify(defaultNode.data))
        console.log('[TopologyTree] setDefaultStateDirectly: defaultNode has children:', defaultNode.children && defaultNode.children.length)
        console.log('[TopologyTree] setDefaultStateDirectly: tree nodes before expand:', this.$refs.tree?.nodes?.map(n => ({ id: n.id, expanded: n.expanded, children: n.children?.length })))

        if (!queryNodeId) {
          RouterQuery.set({
            node: defaultNode.id,
            page: 1,
            _t: Date.now()
          })
        }

        console.log('[TopologyTree] setDefaultStateDirectly: calling tree.setExpanded(', defaultNode.id, ')')
        tree.setExpanded(defaultNode.id)
        
        console.log('[TopologyTree] setDefaultStateDirectly: tree nodes after expand:', this.$refs.tree?.nodes?.map(n => ({ id: n.id, expanded: n.expanded })))
        console.log('[TopologyTree] setDefaultStateDirectly: selected defaultNode:', defaultNode.id)
        
        tree.setSelected(defaultNode.id, { emitEvent: true })
        this.handleDefaultExpand(defaultNode)

        if (!this.initialized) {
          this.initialized = true
        }
      }
      console.log('[TopologyTree] setDefaultStateDirectly: finished')
    },

    saveExpandedState() {
      if (!this.$refs.tree || !this.$refs.tree.nodes) return
      const expandedIds = this.$refs.tree.nodes
        .filter(node => node.expanded)
        .map(node => node.id)
      try {
        sessionStorage.setItem(`topology_expanded_${this.bizId}`, JSON.stringify(expandedIds))
      } catch (e) {
        // ignore
      }
    },

    restoreExpandedState() {
      try {
        const saved = sessionStorage.getItem(`topology_expanded_${this.bizId}`)
        if (!saved) return
        const expandedIds = JSON.parse(saved)
        this.isRestoringExpanded = true
        expandedIds.forEach(id => {
          this.$refs.tree?.setExpanded(id, { emitEvent: false })
        })
        this.$nextTick(() => {
          this.isRestoringExpanded = false
        })
      } catch (e) {
        // ignore
      }
    },

    setDefaultState() {
      console.log('[TopologyTree] setDefaultState: start')
      const queryNodeId = this.$route.query.node || ''
      const queryTopoPathArray = this.$route.query.topo_path ? this.$route.query.topo_path.split(',') : []
      const [firstNode] = this.$refs.tree?.nodes || []

      let defaultNode = null

      if (queryNodeId) {
        defaultNode = this.$refs.tree?.getNodeById(queryNodeId)
      }

      if (!defaultNode && queryTopoPathArray.length) {
        for (let i = queryTopoPathArray.length; i > 0; i--) {
          defaultNode = this.$refs.tree?.getNodeById(queryTopoPathArray[i - 1])
          if (defaultNode) break
        }
      }

      if (!defaultNode) {
        defaultNode = firstNode || this.$refs.tree?.getNodeById(`biz-${this.getCurrentBizId()}`)
      }

      if (defaultNode) {
        const { tree } = this.$refs

        tree.setExpanded(defaultNode.id)
        tree.setSelected(defaultNode.id, { emitEvent: true })
        this.handleDefaultExpand(defaultNode)

        if (!this.initialized) {
          this.initialized = true
        }
      }
      console.log('[TopologyTree] setDefaultState: finished')
    },

    getNodePath(node) {
      const path = []
      let current = node
      while (current) {
        path.unshift(current)
        current = current.parent
      }
      return path
    },

    handleDefaultExpand(node) {
      const nodes = []
      let parentNode = node
      while (parentNode) {
        nodes.push(...(parentNode.children || []))
        if (!parentNode.parent) {
          nodes.push(parentNode)
        }
        parentNode = parentNode.parent
      }
      this.setNodeCount(nodes)
    },

    async setNodeCount(targetNodes, force = false) {
      // 过滤已完成的节点（与原项目保持一致）
      // force参数强制刷新所有节点，否则跳过pending和finished状态的节点
      const nodes = force
        ? targetNodes
        : targetNodes.filter(({ data }) => !['pending', 'finished'].includes(data.status))

      if (!nodes || !Array.isArray(nodes) || !nodes.length) return

      // 过滤出正常节点（biz、set、module）
      const normalNodes = nodes.filter(n => n.data && ['biz', 'set', 'module'].includes(n.data.bk_obj_id))
      if (!normalNodes.length) return

      // 设置所有节点状态为pending（开始加载）
      normalNodes.forEach(({ data }) => this.$set(data, 'status', 'pending'))

      try {
        const condition = normalNodes.map(({ data }) => ({
          bk_obj_id: data.bk_obj_id,
          bk_inst_id: data.bk_inst_id,
          bk_biz_id: data.bk_biz_id || this.bizId
        }))

        const response = await topoAPI.getTopoStatistics(this.bizId, { condition })
        const results = response.data || []

        // 设置成功状态和统计数据
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
        // 设置错误状态
        normalNodes.forEach((node) => {
          this.$set(node.data, 'status', 'error')
        })
      }
    },

    getNodeId(data) {
      return `${data.bk_obj_id}-${data.bk_inst_id}`
    },

    isContainerNode(node) {
      return node.data?.is_container
    },

    genTopoPathByNode(node) {
      const path = []
      let currentNode = node
      while (currentNode.parent) {
        path.push(this.getNodeId(currentNode.data))
        currentNode = currentNode.parent
      }
      return path.reverse()
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
      const oldId = this.$route.query.node
      const newId = node.id

      this.$emit('node-select', node)

      if (oldId === newId) {
        return
      }

      const currentPage = this.$route.query.page || 1
      const query = {
        node: newId,
        page: currentPage,
        _t: Date.now()
      }

      if (this.isContainerNode(node)) {
        query.topo_path = this.genTopoPathByNode(node).join(',')
      } else {
        query.topo_path = undefined
      }

      RouterQuery.set(query)
    },

    handleExpandChange(node) {
      if (node.data?.bk_obj_id === 'biz' && !node.expanded) {
        this.$nextTick(() => {
          this.$refs.tree?.setExpanded(node.id, { emitEvent: false })
        })
        return
      }

      if (!node.expanded || this.isRestoringExpanded) {
        this.saveExpandedState()
        return
      }

      this.setNodeCount([node, ...node.children])
      this.saveExpandedState()
    },

    updateTreeHeight() {
      const container = this.$el.parentElement
      if (container) {
        this.treeHeight = container.clientHeight - 60
      }
    },

    // 点击新建按钮，打开新建对话框
    handleShowCreateDialog(node) {
      this.createDialog = {
        visible: true,
        parentNode: node
      }
    },
    // 新建集群提交
    handleCreateSetSubmit(data) {
      console.log('[TopologyTree] handleCreateSetSubmit:', data)
      this.$bkMessage({
        theme: 'primary',
        message: `创建集群：${data.names.join(', ')}`
      })
      this.createDialog.visible = false
    },
    // 取消新建
    handleCancelCreate() {
      this.createDialog.visible = false
      this.createDialog.parentNode = null
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