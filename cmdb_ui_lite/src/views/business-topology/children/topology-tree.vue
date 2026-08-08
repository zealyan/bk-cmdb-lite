<template>
  <section class="tree-layout" v-bkloading="{ isLoading: loading, opacity: 1 }">
    <bk-input class="tree-search"
      clearable
      right-icon="bk-icon icon-search"
      placeholder="请输入关键词"
      v-model.trim="filterKeyword"
      @input="handleFilterThrottled">
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

    <!-- 新建集群对话框 (在biz节点上新建) -->
    <bk-dialog class="bk-dialog-no-padding"
      v-model="createSetDialog.visible"
      :show-footer="false"
      :mask-close="false"
      :width="580"
      @cancel="handleCancelCreate">
      <create-set v-if="createSetDialog.visible"
        :parent-node="createSetDialog.parentNode"
        @submit="handleCreateSetSubmit"
        @cancel="handleCancelCreate">
      </create-set>
    </bk-dialog>

    <!-- 新建模块对话框 (在set节点上新建) -->
    <bk-dialog class="bk-dialog-no-padding"
      v-model="createModuleDialog.visible"
      :show-footer="false"
      :mask-close="false"
      :width="580"
      @cancel="handleCancelCreate">
      <create-module v-if="createModuleDialog.visible"
        :parent-node="createModuleDialog.parentNode"
        @submit="handleCreateModuleSubmit"
        @cancel="handleCancelCreate">
      </create-module>
    </bk-dialog>
  </section>
</template>

<script>
import TopologyTreeNode from './topology-tree-node.vue'
import CreateSet from './create-set.vue'
import CreateModule from './create-module.vue'
import { topoAPI } from '@/api/topo'
import { cancelRequest, isCancelError } from '@/api/client'
import RouterQuery from '@/utils/router-query'
import { MENU_BUSINESS_TOPOLOGY } from '@/dictionary/menu-symbol'
import throttle from 'lodash/throttle'

const MODEL_INFO = {
  biz: { bk_obj_name: '业务', icon_text: '业' },
  set: { bk_obj_name: '集群', icon_text: '集' },
  module: { bk_obj_name: '模块', icon_text: '模' }
}

export default {
  name: 'TopologyTree',
  components: {
    TopologyTreeNode,
    CreateSet,
    CreateModule
  },
  props: {
    active: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      // 复刻原项目：filterKeyword 初始化时从 URL 的 keyword 参数恢复，
      // 保证从其他子路由（如主机详情）返回业务拓扑后，输入的“关系词/关键词”
      // 不丢失。对应原项目 src/ui/.../topology-tree.vue: filter: RouterQuery.get('keyword', '')
      filterKeyword: RouterQuery.get('keyword', ''),
      nodeCountType: 'host_count',
      treeHeight: 600,
      treeData: [],
      loading: false,
      loadedNodes: new Set(),
      initialized: false,
      bizId: null,
      isRestoringExpanded: false,
      createSetDialog: {
        visible: false,
        parentNode: null
      },
      createModuleDialog: {
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
    // 复刻上游 bk-cmdb：搜索框输入做 300ms 节流，避免逐字符触发 tree.filter + setNodeCount
    // （对可见节点批量统计）造成的大量重算与 DOM 抖动；lodash throttle 默认 trailing=true，
    // 保证最后一次输入的最终结果一定生效。
    this.handleFilterThrottled = throttle(this.handleFilter, 300)
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
    // 取消进行中的拓扑加载与统计请求，释放数据引用（GC）；并清空待执行的节流搜索
    cancelRequest('topo-load')
    cancelRequest('topo-statistics')
    this.handleFilterThrottled && this.handleFilterThrottled.cancel()
  },
  methods: {
    async initTopology() {
      console.log('[TopologyTree] initTopology: start')
      this.loading = true
      try {
        const topology = await this.getInstanceTopology()
        console.log('[TopologyTree] initTopology: topology data loaded:', topology)
        console.log('[TopologyTree] initTopology: topology type:', typeof topology)
        console.log('[TopologyTree] initTopology: topology length:', topology && topology.length)
        console.log('[TopologyTree] initTopology: first node:', topology && topology[0] ? topology[0].bk_inst_name : 'null')

        this.treeData = topology || []
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

      const res = await topoAPI.getInstanceTopo(bizId, { with_statistics: true },
        { requestId: 'topo-load', cancelPrevious: true })
      const data = res || {}

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

      // 复刻原项目：从其他子路由（如主机详情）返回业务拓扑后，
      // filterKeyword 已从 URL 的 keyword 参数恢复，此处重新对拓扑树执行搜索过滤，
      // 保证输入的“关系词/关键词”不丢失且搜索结果被还原。
      // 对应原项目 src/ui/.../topology-tree.vue getDefaultNode() 中 keyword 分支的 tree.filter(keyword)。
      if (this.filterKeyword) {
        this.handleFilter()
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
      // 复刻原项目 bk-cmdb：仅在「业务拓扑主页面」(route === MENU_BUSINESS_TOPOLOGY) 才依据 URL 的
      // node 参数定位 / 展开拓扑树。主机详情是嵌套子路由 (route === MENU_BUSINESS_HOST_DETAILS)，
      // 进入详情时父组件（含拓扑树）仍常驻内存，若此处缺少路由名守卫，会在【详情页隐藏期间】因 node
      // 变化而偷偷重定位树，返回业务拓扑时便表现为一次多余的"跳动 / 刷新"。
      // 原项目 src/ui/.../topology-tree.vue 的 setDefaultState 即以此为前置条件，lite 此处对齐。
      if (this.$route.name !== MENU_BUSINESS_TOPOLOGY) return
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

        // 节点快速展开/切换时，用 requestId 取消上一批未完成的统计请求，
        // 避免陈旧统计结果在竞态下回写节点 status/host_count，造成数量标签闪烁。
        const response = await topoAPI.getTopoStatistics(this.bizId, { condition },
          { requestId: 'topo-statistics', cancelPrevious: true })
        const results = response || []

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
        // 请求被取消（节点快速展开/切换时的 cancelPrevious）属预期行为，静默忽略，
        // 不将该批次节点标记为 error，避免数量标签误闪。
        if (isCancelError(error)) {
          console.log('[TopologyTree] 统计请求已取消（被新请求取代）')
          return
        }
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

      // 切换到新拓扑节点时，页码必须重置为第 1 页。
      // 节点是分页上下文：旧节点的页码对目标节点无意义，需“重置/消亡”旧页码并重建为 1，
      // 否则会出现“路由到新 node 后 page 参数未更新、用旧页码加载新节点数据”的问题。
      // 对齐原项目 src/ui/src/views/business-topology/children/topology-tree.vue
      // handleSelectChange：query 始终携带 page: 1。
      const query = {
        node: newId,
        page: 1,
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

      this.setNodeCount([node, ...(node.children || [])])
      this.saveExpandedState()
    },

    updateTreeHeight() {
      const container = this.$el.parentElement
      if (container) {
        this.treeHeight = container.clientHeight - 60
      }
    },

    // 点击新建按钮，根据节点类型打开不同对话框
    handleShowCreateDialog(node) {
      const objId = node.data?.bk_obj_id
      console.log('[TopologyTree] handleShowCreateDialog:', { node, objId })

      if (objId === 'biz') {
        // 在业务节点上新建集群
        this.createSetDialog = {
          visible: true,
          parentNode: node
        }
      } else if (objId === 'set') {
        // 在集群节点上新建模块
        this.createModuleDialog = {
          visible: true,
          parentNode: node
        }
      }
    },

    // 新建集群提交
    async handleCreateSetSubmit(data) {
      console.log('[TopologyTree] handleCreateSetSubmit:', data)
      try {
        const bizId = this.getCurrentBizId()
        const result = await topoAPI.createSet(bizId, {
          names: data.names
        })
        console.log('[TopologyTree] createSet result:', result)
        this.$bkMessage({
          theme: 'success',
          message: `创建集群成功：${data.names.join(', ')}`
        })
        this.createSetDialog.visible = false
        // 刷新拓扑树
        this.initTopology()
      } catch (error) {
        console.error('[TopologyTree] createSet error:', error)
        this.$bkMessage({
          theme: 'error',
          message: `创建集群失败：${error.message || '未知错误'}`
        })
      }
    },

    // 新建模块提交
    async handleCreateModuleSubmit(data) {
      console.log('[TopologyTree] handleCreateModuleSubmit:', data)
      try {
        const bizId = this.getCurrentBizId()
        const parentId = this.createModuleDialog.parentNode?.data?.bk_inst_id

        // 兼容新旧数据结构
        // 新结构: { bk_module_name: string[], service_category_id, service_template_id }
        // 旧结构: { names: string[] }
        const names = Array.isArray(data.bk_module_name) ? data.bk_module_name : data.names

        const result = await topoAPI.createModule(bizId, parentId, {
          names: names,
          service_category_id: data.service_category_id,
          service_template_id: data.service_template_id || 0
        })
        console.log('[TopologyTree] createModule result:', result)
        this.$bkMessage({
          theme: 'success',
          message: `创建模块成功：${names.join(', ')}`
        })
        this.createModuleDialog.visible = false
        // 刷新拓扑树
        this.initTopology()
      } catch (error) {
        console.error('[TopologyTree] createModule error:', error)
        this.$bkMessage({
          theme: 'error',
          message: `创建模块失败：${error.message || '未知错误'}`
        })
      }
    },

    // 取消新建
    handleCancelCreate() {
      this.createSetDialog.visible = false
      this.createSetDialog.parentNode = null
      this.createModuleDialog.visible = false
      this.createModuleDialog.parentNode = null
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