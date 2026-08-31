<template>
  <div class="layout" v-bkloading="{ isLoading: pageLoading, opacity: 1 }">
    <div class="topology-layout" ref="topologyLayout">
      <div
        class="left-panel"
        :class="{ 'is-collapsed': leftCollapsed }"
        :style="{ width: leftWidth + 'px' }">
        <topology-tree
          ref="topologyTree"
          :active="activeTab"
          @node-select="handleNodeSelect">
        </topology-tree>

        <div
          class="resize-handler"
          @mousedown.left="handleResizeStart"
          @dblclick="toggleLeftPanel">
        </div>
      </div>

      <i
        class="topology-collapse-icon bk-icon icon-angle-left"
        :class="{ 'is-collapsed': leftCollapsed }"
        :style="{ left: (leftCollapsed ? 0 : leftWidth) + 'px' }"
        @click="toggleLeftPanel">
      </i>

      <i class="resize-proxy" ref="resizeProxy"></i>
      <div class="resize-mask" ref="resizeMask"></div>

      <div class="right-panel">
        <bk-tab class="topology-tab" type="unborder-card" :active.sync="activeTab" @tab-change="handleTabChange">
          <bk-tab-panel name="hostList" label="主机列表">
            <div v-if="!selectedNode" class="empty-state">
              <div class="placeholder-text">请选择拓扑节点</div>
              <div class="placeholder-desc">点击左侧拓扑树节点查看主机列表</div>
            </div>
            <host-list
              v-else
              :active="activeTab === 'hostList'"
              :node="selectedNode"
              ref="hostList"
              @transfer-complete="handleTransferComplete">
            </host-list>
          </bk-tab-panel>

          <!-- 服务实例 tab：暂未开发实现，先注释隐藏 -->
          <!-- <bk-tab-panel name="serviceInstance" label="服务实例">
            <div v-if="!selectedNode" class="empty-state">
              <div class="placeholder-text">请选择拓扑节点</div>
              <div class="placeholder-desc">点击左侧拓扑树节点查看服务实例</div>
            </div>
            <div v-else-if="selectedNode.data.bk_obj_id !== 'module'" class="empty-state">
              <div class="placeholder-text">非业务模块</div>
              <div class="placeholder-desc">请选择业务模块查看服务实例</div>
            </div>
            <div v-else class="service-instance-content">
              <div class="placeholder-text">{{ selectedNode.data.bk_inst_name }} - 服务实例</div>
              <div class="placeholder-desc">服务实例数量: {{ selectedNode.data.host_count || 0 }}</div>
              <div class="placeholder-desc">待开发：服务实例列表数据表格</div>
            </div>
          </bk-tab-panel> -->

          <bk-tab-panel name="nodeInfo" label="节点信息" render-directive="if">
            <div v-if="!selectedNode" class="empty-state">
              <div class="placeholder-text">请选择拓扑节点</div>
              <div class="placeholder-desc">点击左侧拓扑树节点查看节点信息</div>
            </div>
            <node-info v-else :node="selectedNode" @deleted="handleNodeDeleted" @updated="handleNodeUpdated"></node-info>
          </bk-tab-panel>

          <bk-tab-panel name="association" label="关联" render-directive="if">
            <div v-if="!selectedNode" class="empty-state">
              <div class="placeholder-text">请选择拓扑节点</div>
              <div class="placeholder-desc">点击左侧拓扑树节点查看关联</div>
            </div>
            <node-association v-else :node="selectedNode"></node-association>
          </bk-tab-panel>
        </bk-tab>
      </div>

      <!-- 主机详情浮层：复刻原项目 bk-cmdb 的 <router-subview> 机制。
           host/:id 已声明为「业务拓扑(index)」的嵌套子路由，故此处 <router-view>
           仅在命中该子路由时渲染 host-details/index.vue，并以绝对定位全屏浮层
           (position:absolute; top:0; left:0; width/height:100%; z-index:100; background:#fff)
           覆盖在拓扑视图之上。业务拓扑视图（含拓扑树）在整个过程中 NEVER 卸载，
           因此拓扑树的节点展开状态（保存在 bk-big-tree 组件内存）始终保留：
           - 进入主机详情：父组件保持挂载，仅浮层叠加显示，拓扑树不重建、不重置；
           - 返回主机列表：仅关闭浮层，拓扑树原样保留，不触发任何重载；
           - 主机列表重加载由 host-list 内的 RouterQuery.watch('*') 在 query.page
             变化时自动触发（返回时 page 由缺省恢复为 1），无需在此额外处理。 -->
      <router-view class="host-detail-subview"></router-view>
    </div>
  </div>
</template>

<script>
import TopologyTree from './children/topology-tree.vue'
import HostList from './host/host-list.vue'
import NodeInfo from './children/node-info.vue'
import NodeAssociation from './children/node-association.vue'
import RouterQuery from '@/utils/router-query'
import { MENU_BUSINESS_TOPOLOGY, MENU_BUSINESS_HOST_DETAILS } from '@/dictionary/menu-symbol'

export default {
  name: 'BusinessTopology',
  components: {
    TopologyTree,
    HostList,
    NodeInfo,
    NodeAssociation
  },
  data() {
    return {
      leftWidth: 286,
      leftCollapsed: false,
      resizeState: {},
      minWidth: 200,
      maxWidth: 480,
      activeTab: RouterQuery.get('tab', 'hostList'),
      selectedNode: null,
      pageLoading: true
    }
  },
  computed: {
    bizId() {
      // 必须做类型归一：URL 直接解析出的 params.bizId 是字符串 '2'，
      // 而编程式导航（如主机详情返回时 router.replace({ params: { bizId: 2 } })）
      // 传入的可能是数字 2。若不归一，'2' -> 2 会被 watch 判定为「业务切换」，
      // 从而误触发 initTopology() 让整棵拓扑树重新拉取并转圈（表现为首次返回刷新一次）。
      const raw = this.$route.params.bizId
      const num = parseInt(raw, 10)
      return Number.isNaN(num) ? null : num
    }
  },
  watch: {
    activeTab(value) {
      const query = {
        tab: value,
        node: RouterQuery.get('node'),
        _t: Date.now()
      }
      const page = RouterQuery.get('page')
      if (page !== null && page !== undefined && page !== '') {
        query.page = page
      }
      RouterQuery.setAll(query)
    },
    bizId(value, oldValue) {
      // 仅在「业务真正切换」时重建拓扑树；相同业务（含类型漂移导致的伪变化）直接忽略
      if (value === null || value === oldValue) return
      this.$nextTick(() => {
        this.$refs.topologyTree?.initTopology()
      })
    },
    '$route'(to, from) {
      // 复刻原项目 bk-cmdb 的业务拓扑交互：
      // 主机详情(host/:id) 作为「业务拓扑(index)」的嵌套子路由，进入时父组件保持挂载、
      // 拓扑树不刷新；而从主机详情【返回】业务拓扑时，应重新加载右侧「主机列表」数据
      // （原项目返回即刷新列表，例如主机在详情页被编辑/转移后，回到列表能看到最新数据）。
      // 由于嵌套路由下 host-list 组件不再随返回而 remount（created 不重跑），
      // 此处显式在返回瞬间触发一次列表重载；拓扑树因父组件常驻不受影响。
      if (to.name === MENU_BUSINESS_TOPOLOGY && from.name === MENU_BUSINESS_HOST_DETAILS) {
        this.$nextTick(() => {
          this.$refs.hostList?.loadHostList()
        })
      }
    }
  },
  async beforeRouteLeave(to, from, next) {
    this.$refs.topologyTree?.saveExpandedState()
    next()
  },
  created() {
    console.log('[BusinessTopology] created: start')
    console.log('[BusinessTopology] created: route:', this.$route.fullPath)
    console.log('[BusinessTopology] created: params:', this.$route.params)
    console.log('[BusinessTopology] created: query:', this.$route.query)

    this.unwatch = RouterQuery.watch('tab', (value = 'hostList') => {
      this.activeTab = value
    })

    this.$nextTick(() => {
      setTimeout(() => {
        this.pageLoading = false
      }, 300)
    })
  },
  mounted() {
    console.log('[BusinessTopology] mounted: start')
    console.log('[BusinessTopology] mounted: topologyTree ref:', this.$refs.topologyTree)
  },
  beforeDestroy() {
    document.removeEventListener('mousemove', this.handleResizeMove)
    document.removeEventListener('mouseup', this.handleResizeEnd)
    this.unwatch && this.unwatch()
  },
  methods: {
    toggleLeftPanel() {
      this.leftCollapsed = !this.leftCollapsed
    },
    handleResizeStart(event) {
      if (this.leftCollapsed) return
      const $handler = event.currentTarget
      const $layout = this.$refs.topologyLayout
      const layoutRect = $layout.getBoundingClientRect()
      const $resizeProxy = this.$refs.resizeProxy
      const $resizeMask = this.$refs.resizeMask

      $resizeProxy.style.visibility = 'visible'
      $resizeMask.style.display = 'block'

      const handlerRight = $handler.getBoundingClientRect().right - layoutRect.left

      this.resizeState = {
        startMouseLeft: event.clientX - layoutRect.left,
        startLeft: handlerRight
      }

      $resizeProxy.style.top = '0'
      $resizeProxy.style.left = `${this.resizeState.startLeft}px`
      $resizeProxy.style.height = '100%'
      $resizeMask.style.cursor = 'col-resize'

      document.onselectstart = () => false
      document.ondragstart = () => false

      document.addEventListener('mousemove', this.handleResizeMove)
      document.addEventListener('mouseup', this.handleResizeEnd)
    },
    handleResizeMove(event) {
      const $resizeProxy = this.$refs.resizeProxy
      const $layout = this.$refs.topologyLayout
      const layoutRect = $layout.getBoundingClientRect()

      const mouseLeft = event.clientX - layoutRect.left
      const deltaLeft = mouseLeft - this.resizeState.startMouseLeft
      const proxyLeft = this.resizeState.startLeft + deltaLeft
      const clampedLeft = Math.min(this.maxWidth, Math.max(this.minWidth, proxyLeft))
      $resizeProxy.style.left = `${clampedLeft}px`
    },
    handleResizeEnd() {
      const $resizeProxy = this.$refs.resizeProxy
      const $resizeMask = this.$refs.resizeMask

      const finalLeft = parseInt($resizeProxy.style.left, 10)
      this.leftWidth = finalLeft

      $resizeProxy.style.visibility = 'hidden'
      $resizeMask.style.display = 'none'

      document.removeEventListener('mousemove', this.handleResizeMove)
      document.removeEventListener('mouseup', this.handleResizeEnd)
      document.onselectstart = null
      document.ondragstart = null
    },
    handleTabChange(name) {
      const query = {
        tab: name,
        node: RouterQuery.get('node'),
        _t: Date.now()
      }
      const page = RouterQuery.get('page')
      if (page !== null && page !== undefined && page !== '') {
        query.page = page
      }
      RouterQuery.setAll(query)
    },
    handleNodeSelect(node) {
      this.selectedNode = node
    },
    handleNodeDeleted() {
      // 节点删除后刷新拓扑树
      this.selectedNode = null
      this.$refs.topologyTree.initTopology()
    },
    handleNodeUpdated() {
      // 节点属性更新后刷新拓扑树（同步节点展示名称 bk_inst_name）
      // 与原项目一致：编辑成功后重新拉取拓扑，避免树节点标签滞留旧值
      this.$refs.topologyTree.initTopology()
    },
    handleTransferComplete(payload) {
      // 主机转移完成后刷新拓扑树统计数据（host_count 等）
      console.log('[BusinessTopology] 主机转移完成，刷新拓扑树:', payload)
      this.$refs.topologyTree.initTopology()
    }
  }
}
</script>

<style lang="scss" scoped>
.layout {
  height: 100%;
  width: 100%;
  overflow: hidden;
  background: #fff;
  /* 作为主机详情浮层(.host-detail-subview)的定位上下文，
     保证浮层相对业务拓扑视图全屏覆盖，而非相对更外层容器 */
  position: relative;
}

/* 主机详情浮层：复刻原项目 bk-cmdb <router-subview> 的 overlay 样式。
   绝对定位 + 白底 + z-index:100，仅在命中嵌套子路由 host/:id 时由
   <router-view class="host-detail-subview"> 渲染 host-details/index.vue，
   覆盖在拓扑视图之上；业务拓扑（含拓扑树）保持挂载不被卸载。 */
.host-detail-subview {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 100;
  background-color: #fff;
  overflow: hidden;
}

.topology-layout {
  display: flex;
  height: 100%;
  width: 100%;
  position: relative;
}

.left-panel,
.right-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.left-panel {
  position: relative;
  flex-shrink: 0;
  border-right: 1px solid $cmdbLayoutBorderColor;
  transition: width 0.2s ease;
  overflow: visible;
  padding-top: 10px;
  box-sizing: border-box;
  width: 286px;

  &.is-collapsed {
    width: 0 !important;
    border-right: none;
    overflow: visible;
    padding-top: 0;
  }

  .resize-handler {
    position: absolute;
    top: 0;
    left: 100%;
    width: 5px;
    height: 100%;
    cursor: col-resize;
    background-color: transparent;
    z-index: 10;

    &:hover {
      background-image: linear-gradient(
        to right,
        transparent,
        transparent 2px,
        $primaryColor 2px,
        $primaryColor 3px,
        transparent 3px,
        transparent
      );
    }
  }
}

.right-panel {
  flex: 1;
  min-width: 0;
  height: 100%;
  overflow: hidden;

  .topology-tab {
    height: 100%;

    ::v-deep .bk-tab-header {
      padding: 0;
      margin: 0 20px;
    }

    ::v-deep .bk-tab-section {
      height: calc(100% - 50px);
    }
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 300px;
  padding: 20px;
}

.placeholder-text {
  font-size: 16px;
  color: $grayColor;
  margin-bottom: 8px;
}

.placeholder-desc {
  font-size: 12px;
  color: $textDisabledColor;
  margin-bottom: 4px;
}

.topology-collapse-icon {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  left: 286px;
  width: 16px;
  height: 100px;
  line-height: 100px;
  background: $cmdbLayoutBorderColor;
  border-radius: 0px 12px 12px 0px;
  text-align: center;
  font-size: 20px;
  color: #fff;
  cursor: pointer;
  text-indent: -2px;
  z-index: 20;
  transition: left 0.2s ease, background-color 0.2s;

  &:hover {
    background: #699DF4;
  }

  &.is-collapsed {
    left: 0;

    &:before {
      display: inline-block;
      transform: rotate(180deg);
    }
  }
}

.resize-proxy {
  visibility: hidden;
  position: absolute;
  top: 0;
  height: 100%;
  border-left: 1px dashed $primaryColor;
  pointer-events: none;
  z-index: 99;
}

.resize-mask {
  display: none;
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  z-index: 98;
}

.service-instance-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 300px;
  padding: 20px;
}
</style>
