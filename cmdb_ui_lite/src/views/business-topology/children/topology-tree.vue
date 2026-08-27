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
          :child-model-id="childModelIdOf(data.bk_obj_id)"
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

    <!-- 新建集群对话框 (在set父节点上新建) -->
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

    <!-- 新建自定义主线层对话框 (在 biz/appsys/zone 等节点下新建其直接子层，如 appsys/zone) -->
    <bk-dialog class="bk-dialog-no-padding"
      v-model="createMainlineDialog.visible"
      :show-footer="false"
      :mask-close="false"
      :width="580"
      @cancel="handleCancelCreate">
      <create-mainline-node v-if="createMainlineDialog.visible"
        :parent-node="createMainlineDialog.parentNode"
        :child-model="createMainlineDialog.childModel"
        :child-model-name="createMainlineDialog.childModelName"
        @submit="handleCreateMainlineSubmit"
        @cancel="handleCancelCreate">
      </create-mainline-node>
    </bk-dialog>
  </section>
</template>

<script>
import TopologyTreeNode from './topology-tree-node.vue'
import CreateSet from './create-set.vue'
import CreateModule from './create-module.vue'
import CreateMainlineNode from './create-mainline-node.vue'
import { topoAPI } from '@/api/topo'
import { cancelRequest, isCancelError } from '@/api/client'
import RouterQuery from '@/utils/router-query'
import { MENU_BUSINESS_TOPOLOGY } from '@/dictionary/menu-symbol'
import throttle from 'lodash/throttle'

// ── 虚拟滚动定位参数 ────────────────────────────────────────────────
// bk-big-tree 传入 height 后启用内置 bk-virtual-scroll，只渲染视口内约
// itemNumber 条 DOM。懒加载树逐级展开会持续 addNode → setListData，而
// setListData 内部的 freshDataNoScroll 会「按滚动比例」重算位置，因此
// 必须等列表长度稳定后再滚，并在漂移后重试收敛。
const SCROLL_RETRY = 4 // 最多重试轮数（应对懒加载追加子节点导致的位置漂移）
const SCROLL_POLL_MS = 16 // 轮询间隔，约一帧
const SCROLL_SETTLE_MS = 50 // 大于 virtual-scroll 内部 throttle(30, calcData)
const SCROLL_SYNC_TIMEOUT = 3000 // 等待列表同步的兜底超时

const MODEL_INFO = {
  biz: { bk_obj_name: '业务', icon_text: '业' },
  sys: { bk_obj_name: '应用系统', icon_text: '应' },
  subsys: { bk_obj_name: '应用子系统', icon_text: '子' },
  appsys: { bk_obj_name: '应用系统', icon_text: '应' },
  appsubsys: { bk_obj_name: '应用子系统', icon_text: '子' },
  zone: { bk_obj_name: '片区', icon_text: '片' },
  set: { bk_obj_name: '集群', icon_text: '集' },
  module: { bk_obj_name: '模块', icon_text: '模' }
}

// 递归映射后端主线实例树：保留任意层级结构与正确的 bk_obj_id，
// 不再把树硬编码成 biz→set→module（否则 appsys 等自定义层会被吞掉/错显成 set）。
// 图标首字一律取自「模型名称首字符」（对齐原项目规则：中文『应用系统』取『应』），
// 不再用 obj_id 首字母兜底——新增主线模型（如 app_sys）无需再登记到 MODEL_INFO。
function mapTopoNode(node, bizId, ctx) {
  const objId = node.bk_obj_id
  const info = MODEL_INFO[objId] || {}
  // 名称：优先用后端已注入的 bk_obj_name（含中文名），兜底用 MODEL_INFO / obj_id
  const name = node.bk_obj_name || info.bk_obj_name || objId
  // 记录最近的 set 祖先实例 id，供 module 回填 bk_set_id（即使中间插入了 appsys 等自定义层）
  const nextCtx = { setId: objId === 'set' ? node.bk_inst_id : ctx.setId }
  return {
    ...node,
    ...info,
    bk_obj_name: name,
    // 图标取名称首字符（中文/英文均适用），不再退化成 obj_id 首字母
    icon_text: (name && name[0]) || (objId && objId[0] ? objId[0].toUpperCase() : 'N'),
    bk_obj_id: objId,
    bk_inst_name: node.bk_inst_name,
    default: node.default || 0,
    bk_biz_id: bizId,
    bk_set_id: objId === 'module'
      ? (nextCtx.setId || node.bk_set_id || 0)
      : (node.bk_set_id || 0),
    host_count: node.count || 0,
    service_instance_count: 0,
    child: (node.child || []).map(child => mapTopoNode(child, bizId, nextCtx))
  }
}

export default {
  name: 'TopologyTree',
  components: {
    TopologyTreeNode,
    CreateSet,
    CreateModule,
    CreateMainlineNode
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
      },
      // 自定义主线层（appsys/zone 等）的通用新建对话框状态
      createMainlineDialog: {
        visible: false,
        parentNode: null,
        childModel: '',
        childModelName: ''
      },
      // 主线模型顺序（权威来源，决定"某节点下应创建哪一层"），如 ['biz','appsys','set','module']
      mainlineOrder: []
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
    // 先加载主线模型顺序（决定"某节点下应创建哪一层"），保证首屏新建按钮即正确
    await this.loadMainlineOrder()
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
        const bizId = this.getCurrentBizId()
        this.bizId = bizId
        // 全量加载整棵主线拓扑树（对齐原项目）：
        // 一次性 setData 所有层级节点，keyword 过滤 / URL node 定位直接命中任意层级，
        // 无需懒加载兜底。数据规模由 seed 脚本控制在合理范围（≤1 万节点）。
        const bizInfo = MODEL_INFO.biz || { bk_obj_name: '业务', icon_text: '业' }
        const [topo] = await this.getInstanceTopology()
        if (!topo || topo.bk_inst_id == null) {
          this.treeData = []
          return
        }
        // 根节点必须携带 bk_obj_name/icon_text/bk_biz_id：
        // 图标按"模型中文首个字"渲染（业务 → "业"），host-list 查询依赖 bk_biz_id。
        topo.bk_obj_name = topo.bk_obj_name || bizInfo.bk_obj_name
        topo.icon_text = topo.icon_text || bizInfo.icon_text
        topo.bk_biz_id = bizId
        this.treeData = [topo]
        this.$refs.tree.setData(this.treeData)
        await this.$nextTick()
        await this.setDefaultStateDirectly()
        this.createWatcher()
      } catch (e) {
        console.error('[TopologyTree] initTopology: error:', e)
        this.treeData = []
      } finally {
        this.loading = false
      }
    },

    // 获取业务名称（用于根节点展示），失败回退到 `业务{bizId}`
    async getBizName(bizId) {
      try {
        const list = await topoAPI.getBizList()
        const data = (list && (list.data || list)) || []
        const biz = data.find(b => b.bk_biz_id === bizId)
        return biz ? biz.bk_biz_name : `业务${bizId}`
      } catch (e) {
        return `业务${bizId}`
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

      // 递归映射后端返回的任意层级主线实例树（支持 appsys 等自定义层），
      // 保留正确的 bk_obj_id 与各层 child，不再把结构硬编码成 biz→set→module。
      // 注：当前前端已改为 lazy-method 分层懒加载（见 initTopology），此方法保留
      // 以备非懒加载场景/兼容。
      return [mapTopoNode(data, bizId, { setId: null })]
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
        // 反向同步：URL 中 keyword 变化（前进/后退、外部修改）时，
        // 同步驱动拓扑树按关键词过滤，保证视图与 URL 一致。
        // 输入场景已由模板 @input="handleFilterThrottled" 覆盖，此处补齐导航/外部变更场景。
        this.$nextTick(() => this.handleFilter && this.handleFilter())
      })
    },

    destroyWatcher() {
      this.nodeUnwatch && this.nodeUnwatch()
      this.filterUnwatch && this.filterUnwatch()
    },

    async setDefaultStateDirectly() {
      console.log('[TopologyTree] setDefaultStateDirectly: start')
      const queryNodeId = this.$route.query.node || ''
      const bizId = this.getCurrentBizId()
      const [firstNode] = this.$refs.tree?.nodes || []

      let defaultNode = null

      if (queryNodeId) {
        defaultNode = this.$refs.tree?.getNodeById(queryNodeId)
      }

      // 全量树：任意层级节点已在树中，getNodeById 直接命中（无需路径恢复）
      if (!defaultNode) {
        defaultNode = firstNode || this.$refs.tree?.getNodeById(`biz-${bizId}`)
      }

      if (defaultNode) {
        const { tree } = this.$refs

        if (!queryNodeId) {
          RouterQuery.set({
            node: defaultNode.id,
            page: 1,
            _t: Date.now()
          })
        }

        tree.setExpanded(defaultNode.id)
        tree.setSelected(defaultNode.id, { emitEvent: true })
        this.handleDefaultExpand(defaultNode)

        // 链路最后一环：把选中节点滚入视图。
        // 前面只完成了「展开父链 → 选中」，虚拟滚动下节点数量多时目标行仍在视口外。
        await this.scrollNodeIntoView(defaultNode)

        this.initialized = true
      }

      // 复刻原项目：从其他子路由（如主机详情）返回业务拓扑后，
      // filterKeyword 已从 URL 的 keyword 参数恢复，此处重新对拓扑树执行搜索过滤，
      // 保证输入的“关系词/关键词”不丢失且搜索结果被还原。
      // 对应原项目 src/ui/.../topology-tree.vue getDefaultNode() 中 keyword 分支的 tree.filter(keyword)。
      if (this.filterKeyword) {
        await this.handleFilter()
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

    async setDefaultState() {
      // 复刻原项目 bk-cmdb：仅在「业务拓扑主页面」(route === MENU_BUSINESS_TOPOLOGY) 才依据 URL 的
      // node 参数定位 / 展开拓扑树。主机详情是嵌套子路由 (route === MENU_BUSINESS_HOST_DETAILS)，
      // 进入详情时父组件（含拓扑树）仍常驻内存，若此处缺少路由名守卫，会在【详情页隐藏期间】因 node
      // 变化而偷偷重定位树，返回业务拓扑时便表现为一次多余的"跳动 / 刷新"。
      // 原项目 src/ui/.../topology-tree.vue 的 setDefaultState 即以此为前置条件，lite 此处对齐。
      if (this.$route.name !== MENU_BUSINESS_TOPOLOGY) return
      console.log('[TopologyTree] setDefaultState: start')
      const queryNodeId = this.$route.query.node || ''
      const [firstNode] = this.$refs.tree?.nodes || []

      let defaultNode = null

      if (queryNodeId) {
        defaultNode = this.$refs.tree?.getNodeById(queryNodeId)
      }

      // 全量树：任意层级节点已在树中，getNodeById 直接命中（无需路径恢复 / topo_path 兜底）
      if (!defaultNode) {
        defaultNode = firstNode || this.$refs.tree?.getNodeById(`biz-${this.getCurrentBizId()}`)
      }

      if (defaultNode) {
        const { tree } = this.$refs

        tree.setExpanded(defaultNode.id)
        tree.setSelected(defaultNode.id, { emitEvent: true })
        this.handleDefaultExpand(defaultNode)

        // 链路最后一环：把选中节点滚入视图。
        // 不同于原项目的 `!this.initialized` 单次限制，这里每次 node 变化都尝试滚动，
        // 由 isIndexInViewport 兜底——用户手动点击的节点必然已在视口内、不会被滚动打断；
        // 而「从主机详情/其他页面跳回」「URL 直接改 node」等场景下目标常在视口外，需要滚。
        await this.scrollNodeIntoView(defaultNode)

        // 复刻原项目：node 切换后若 URL 仍携带 keyword，重新对拓扑树执行关键词过滤，
        // 保证「选中节点」与「关键词过滤」两种视图状态在导航后不丢失。
        // 对应 setDefaultStateDirectly 末尾对 filterKeyword 的处理。
        if (this.filterKeyword) {
          await this.handleFilter()
        }

        this.initialized = true
      }
    },

    // ── 虚拟滚动定位：把「视口外」的目标节点滚入视图 ─────────────────────
    // 链路最后一环。全量树一次性 setData，setExpanded 展开父链后
    // setSelected 也只改数据状态；但 bk-big-tree 启用虚拟滚动后 DOM 中仅存在
    // 视口内的 ~itemNumber 条，节点多时目标高亮行仍在视口外，表现为
    // 「URL 带 node 进来，树看着没反应，得手动滚很久才找到选中的节点」。
    //
    // 复刻原项目 src/ui/src/views/business-topology/children/topology-tree.vue：
    //   const index = tree.visibleNodes.indexOf(defaultNode)
    //   tree.$refs.virtualScroll.scrollPageByIndex(index)
    // visibleNodes 是「当前展开态下可见节点」的扁平数组，其下标恰好等于
    // virtualScroll 的行号（setListData(visibleNodes) 使两者一一对应），
    // 所以 indexOf 就是虚拟列表里的目标行，scrollPageByIndex 按 itemHeight
    // 换算出滚动高度并重算渲染窗口。
    //
    // 在原项目基础上补三点，都是懒加载树才会遇到的：
    //   1) 等 virtualScroll 列表与 visibleNodes 同步再取 index —— big-tree 的
    //      setVirtualScrollList 内部还有一层 $nextTick，过早滚动会被随后
    //      setListData 的 freshDataNoScroll（按比例重算）覆盖；
    //   2) 目标已在视口内就不滚，避免用户点击树节点（也会写 URL）时画面跳动；
    //   3) 滚完若懒加载又追加子节点致位置漂移，则重试收敛。
    async scrollNodeIntoView(node) {
      const tree = this.$refs.tree
      if (!tree || !node) return false

      // 最新调用优先：node 连续变化时放弃过期的滚动，避免相互拉扯
      this._scrollToken = (this._scrollToken || 0) + 1
      const token = this._scrollToken

      const vs = tree.$refs.virtualScroll
      // 未启用虚拟滚动（未传 height）时退化为原生 DOM 滚动
      if (!vs) return this.scrollNodeIntoViewByDom(node)

      for (let round = 0; round < SCROLL_RETRY; round++) {
        await this.waitVirtualScrollSynced()
        if (token !== this._scrollToken) return false
        if (!this.$refs.tree || !this.$refs.tree.$refs.virtualScroll) return false

        const index = this.$refs.tree.visibleNodes.indexOf(node)
        if (index < 0) return false
        // 全部条目都能塞进视口，无需滚动
        if (!vs.itemNumber || vs.totalNumber <= vs.itemNumber) return true
        if (this.isIndexInViewport(vs, index)) return true

        // 目标落在视口约 1/3 处：上方留出父链上下文，比顶死更易读
        const offset = Math.floor(vs.itemNumber / 3)
        vs.scrollPageByIndex(Math.max(index - offset, 0))
        // calcList 是 throttle(30, calcData)，给它一拍去落地渲染窗口
        await new Promise(resolve => setTimeout(resolve, SCROLL_SETTLE_MS))
      }
      return true
    },

    // 等 bk-virtual-scroll 内部列表（allListData）与 tree.visibleNodes 同步且长度稳定。
    // 懒加载展开会持续 addNode → setVirtualScrollList，长度未稳时滚动位置会被重算。
    async waitVirtualScrollSynced() {
      const deadline = Date.now() + SCROLL_SYNC_TIMEOUT
      let lastLength = -1
      let stableCount = 0
      while (Date.now() < deadline) {
        const tree = this.$refs.tree
        const vs = tree && tree.$refs.virtualScroll
        if (!tree || !vs) return false
        const { length } = tree.visibleNodes
        if (vs.totalNumber === length && length === lastLength) {
          stableCount += 1
          // 连续两次采样一致才认为稳定，规避单帧巧合
          if (stableCount >= 2) return true
        } else {
          stableCount = 0
        }
        lastLength = length
        await new Promise(resolve => setTimeout(resolve, SCROLL_POLL_MS))
      }
      // 超时也放行：滚一次总比让用户停在视口外好
      return true
    },

    // 基于 virtualScroll 当前渲染窗口判断 index（0-based）是否已在视口内。
    // indexList 里的 value 是 1-based，且 calcData 首尾各多渲染一条
    // （startIndex 会 -1、endIndex = startIndex + itemNumber），故边界向内
    // 收缩一格，避免「贴着边缘只露半行」被误判为可见。
    isIndexInViewport(vs, index) {
      const { indexList } = vs
      if (!indexList || !indexList.length) return false
      const first = indexList[0].value
      const last = indexList[indexList.length - 1].value
      const target = index + 1
      return target > first && target < last
    },

    // 未启用虚拟滚动时的兜底：把选中行的 DOM 滚到容器中间
    scrollNodeIntoViewByDom() {
      const el = this.$el.querySelector('.bk-big-tree-node.is-selected')
      if (el && el.scrollIntoView) {
        el.scrollIntoView({ block: 'center' })
        return true
      }
      return false
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

      // 过滤出需统计的主线节点：含 biz/set/module 及自定义主线层（如 appsys），
      // 只要具备 bk_inst_id 即参与统计（自定义层经后端递归聚合其下 module 主机数）
      const normalNodes = nodes.filter(n => n.data && n.data.bk_inst_id != null
        && n.data.bk_obj_id !== 'host')
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
      if (!this.filterKeyword) {
        this.$refs.tree.filter('')
        return
      }
      // 全量树：tree.filter 递归匹配任意层级已加载节点（对齐原项目），
      // 无需后端搜索 / 路径展开兜底。无匹配时树显示空态由 bk-big-tree 处理。
      this.$refs.tree.filter(this.filterKeyword)
      this.$nextTick(() => {
        this.setNodeCount(this.$refs.tree.visibleNodes)
      })
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

    // 加载主线模型顺序（最左路径扁平列表，如 ['biz','appsys','set','module']）
    async loadMainlineOrder() {
      try {
        const order = await topoAPI.getMainlineModelTree()
        if (Array.isArray(order) && order.length) {
          this.mainlineOrder = order
        }
      } catch (e) {
        console.error('[TopologyTree] 加载主线模型顺序失败:', e)
      }
    },

    // 根据主线顺序，返回某模型的直接子层模型ID（无则 null，表示该层为最底层不可新建）
    childModelIdOf(bkObjId) {
      const order = this.mainlineOrder
      if (!order || !order.length) return ''
      const idx = order.indexOf(bkObjId)
      if (idx < 0 || idx >= order.length - 1) return ''
      return order[idx + 1]
    },

    // 点击新建按钮：按主线顺序在点击节点的【直接子层】创建实例，
    // 严格维持 biz→appsys→zone→set→module 等任意主线顺序，
    // 不再写死 biz→set（否则会在 biz 下错建 set，破坏主线）。
    // - 子层为 set  → 专用新建集群对话框
    // - 子层为 module → 专用新建模块对话框
    // - 子层为自定义层(appsys/zone…) → 通用新建对话框
    handleShowCreateDialog(node) {
      const objId = node.data?.bk_obj_id
      const childModel = this.childModelIdOf(objId)
      console.log('[TopologyTree] handleShowCreateDialog:', { objId, childModel })

      if (!childModel) {
        this.$bkMessage({
          theme: 'warning',
          message: '该层级为最底层，无法在其下新建节点'
        })
        return
      }

      if (childModel === 'set') {
        this.createSetDialog = { visible: true, parentNode: node }
      } else if (childModel === 'module') {
        this.createModuleDialog = { visible: true, parentNode: node }
      } else {
        // 自定义主线层（appsys/zone…）：通用对话框，按子模型动态渲染表单
        const childInfo = MODEL_INFO[childModel] || { bk_obj_name: childModel }
        this.createMainlineDialog = {
          visible: true,
          parentNode: node,
          childModel,
          childModelName: childInfo.bk_obj_name || childModel
        }
      }
    },

    /**
     * 统一呈现「新建主线实例」的返回结果（对齐原项目蓝鲸 CMDB：
     * 重复名称等失败逐条弹拒绝提示，而非静默“创建成功”）。
     *
     * 后端 create_mainline_instance 把单条失败（唯一约束冲突等）汇总到
     * result.data.error_names=[{name, error}]，成功条目在 result.data.created。
     * 这里：
     *  - 失败条目 → 通过 $handleApiError 弹错误提示（含后端可读原因，如“集群名称已存在: X”）；
     *  - 成功条目 → 仅对真正创建的条目弹成功提示（不再用输入名冒充）；
     *  - 返回 { createdCount, errorCount }，由调用方决定是否保持弹窗打开（全部失败时保持）。
     */
    /**
     * 统一处理主线实例创建「成功」分支（遵循框架响应约定）。
     * 失败分支不走这里：后端在部分/全部失败时返回 BaseResp(result:false + bk_error_code)，
     * 经响应拦截器抛异常，由调用方 catch → 全局 this.$handleApiError 统一呈现，
     * 不再在此处手搓提示文案，保证「统一 exception 提示 / 统一业务错误信息」。
     *
     * @param {Object} result 响应拦截器拆包后的 data：{ created:[...], error_names:[] }
     * @param {string} label 模型中文名（集群/模块/自定义层名）
     * @param {Object} dialog 对应弹窗对象（成功则关闭）
     */
    presentCreateSuccess(result, label, dialog) {
      const created = (result.created || [])
        .map(item => item.bk_inst_name)
        .filter(Boolean)
      if (created.length) {
        this.$success(`创建${label}成功：${created.join(', ')}`)
        dialog.visible = false
        this.initTopology()
      }
      // 无成功项（全部失败时不会进入此方法，走 catch）保持弹窗打开以便修正
    },

    // 通用主线层（自定义层）新建提交
    async handleCreateMainlineSubmit(data) {
      console.log('[TopologyTree] handleCreateMainlineSubmit:', data)
      const { parentNode, childModel } = this.createMainlineDialog
      const parentObjId = parentNode.data?.bk_obj_id
      const parentInstId = parentNode.data?.bk_inst_id
      const bizId = parentNode.data?.bk_biz_id || this.getCurrentBizId()
      try {
        const result = await topoAPI.createMainlineInstance({
          parent_obj_id: parentObjId,
          parent_inst_id: parentInstId,
          model_id: childModel,
          names: data.names,
          bk_biz_id: bizId,
          attrs: data.attrs || {}
        })
        console.log('[TopologyTree] createMainlineInstance result:', result)
        this.presentCreateSuccess(result, this.createMainlineDialog.childModelName, this.createMainlineDialog)
      } catch (error) {
        // 部分/全部失败：后端返回 result:false，拦截器抛异常 → 统一业务错误提示
        console.error('[TopologyTree] createMainlineInstance error:', error)
        this.$handleApiError(error)
        // 部分成功：已创建的实例进入拓扑树，刷新显示；弹窗保持打开以便修正失败项
        const created = (error?.response?.data?.data?.created) || []
        if (created.length) this.initTopology()
      }
    },

    // 新建集群提交
    // 关键修复：集群的【父节点】必须来自点击的节点（biz 或自定义层 appsys），
    // 严禁写死 biz。否则在 appsys 下新建 set 时，bk_parent_id 会被写成业务ID，
    // 导致新 set 直接错挂到 biz 下，破坏 biz→appsys→set→module 主线顺序。
    // 统一走通用 createMainlineInstance：由后端按主线顺序设置 bk_parent_id（指向父实例）
    // 与 bk_biz_id（继承父实例），从而无论父是 biz 还是 appsys 都正确下挂。
    async handleCreateSetSubmit(data) {
      console.log('[TopologyTree] handleCreateSetSubmit:', data)
      try {
        const parentNode = this.createSetDialog.parentNode
        const parentObjId = parentNode?.data?.bk_obj_id
        const parentInstId = parentNode?.data?.bk_inst_id
        const bizId = parentNode?.data?.bk_biz_id || this.getCurrentBizId()
        const names = (data && data.names) || []
        if (!parentObjId || parentInstId == null) {
          throw new Error('缺少父节点信息，无法创建集群')
        }
        const result = await topoAPI.createMainlineInstance({
          parent_obj_id: parentObjId,
          parent_inst_id: parentInstId,
          model_id: 'set',
          names: names,
          bk_biz_id: bizId
        })
        console.log('[TopologyTree] createMainlineInstance(set) result:', result)
        this.presentCreateSuccess(result, '集群', this.createSetDialog)
      } catch (error) {
        // 部分/全部失败：统一业务错误提示
        console.error('[TopologyTree] createSet error:', error)
        this.$handleApiError(error)
        const created = (error?.response?.data?.data?.created) || []
        if (created.length) this.initTopology()
      }
    },

    // 新建模块提交
    // 父节点来自点击的节点（set 或自定义层），按主线顺序动态派发，
    // 统一走通用 createMainlineInstance：后端自动设置 bk_parent_id（指向父实例）
    // 并沿主线父链上溯回填 bk_set_id（兼容「set 与 module 间插入自定义层级」，
    // 如 biz→appsys→set→zone→module），不再依赖固定 bk_set_id 入参。
    async handleCreateModuleSubmit(data) {
      console.log('[TopologyTree] handleCreateModuleSubmit:', data)
      try {
        const parentNode = this.createModuleDialog.parentNode
        const parentObjId = parentNode?.data?.bk_obj_id
        const parentInstId = parentNode?.data?.bk_inst_id
        const bizId = parentNode?.data?.bk_biz_id || this.getCurrentBizId()

        // 兼容新旧数据结构
        // 新结构: { bk_module_name: string[], service_category_id, service_template_id }
        // 旧结构: { names: string[] }
        const names = Array.isArray(data.bk_module_name) ? data.bk_module_name : data.names
        if (!parentObjId || parentInstId == null) {
          throw new Error('缺少父节点信息，无法创建模块')
        }

        const result = await topoAPI.createMainlineInstance({
          parent_obj_id: parentObjId,
          parent_inst_id: parentInstId,
          model_id: 'module',
          names: names,
          bk_biz_id: bizId,
          attrs: {
            service_category_id: data.service_category_id,
            service_template_id: data.service_template_id || 0
          }
        })
        console.log('[TopologyTree] createModule result:', result)
        this.presentCreateSuccess(result, '模块', this.createModuleDialog)
      } catch (error) {
        // 部分/全部失败：统一业务错误提示
        console.error('[TopologyTree] createModule error:', error)
        this.$handleApiError(error)
        const created = (error?.response?.data?.data?.created) || []
        if (created.length) this.initTopology()
      }
    },

    // 取消新建
    handleCancelCreate() {
      this.createSetDialog.visible = false
      this.createSetDialog.parentNode = null
      this.createModuleDialog.visible = false
      this.createModuleDialog.parentNode = null
      this.createMainlineDialog.visible = false
      this.createMainlineDialog.parentNode = null
      this.createMainlineDialog.childModel = ''
      this.createMainlineDialog.childModelName = ''
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