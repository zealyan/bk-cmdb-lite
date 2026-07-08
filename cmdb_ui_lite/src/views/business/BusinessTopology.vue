<template>
  <div class="business-topology">
    <div class="topology-layout">
      <div
        class="left-panel"
        :class="{ 'is-collapsed': leftCollapsed }"
        :style="{ width: leftWidth + 'px' }">
        <topology-tree
          ref="topologyTree"
          :active="activeTab"
          @node-select="handleNodeSelect">
        </topology-tree>
      </div>

      <div
        class="resize-handler"
        :class="{ 'is-collapsed': leftCollapsed }"
        @mousedown="handleResizeStart"
        @dblclick="toggleLeftPanel">
        <i
          class="collapse-icon bk-icon"
          :class="leftCollapsed ? 'icon-angle-right' : 'icon-angle-left'"
          @click.stop="toggleLeftPanel">
        </i>
      </div>

      <div class="right-panel">
        <bk-tab class="topology-tab" type="unborder-card" :active.sync="activeTab">
          <!-- 主机列表 Tab -->
          <bk-tab-panel name="hostList" label="主机列表">
            <host-list-panel
              v-if="selectedNode"
              :node="selectedNode"
              :active="activeTab === 'hostList'">
            </host-list-panel>
            <div v-else class="empty-state">
              <div class="placeholder-text">请选择拓扑节点</div>
              <div class="placeholder-desc">点击左侧拓扑树节点查看主机列表</div>
            </div>
          </bk-tab-panel>

          <!-- 服务实例 Tab -->
          <bk-tab-panel name="serviceInstance" label="服务实例">
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
              <div class="placeholder-desc">服务实例数量: {{ selectedNode.data.service_instance_count || 0 }}</div>
              <div class="placeholder-desc">待开发：服务实例列表数据表格</div>
            </div>
          </bk-tab-panel>

          <!-- 节点信息 Tab -->
          <bk-tab-panel name="nodeInfo" label="节点信息">
            <div v-if="!selectedNode" class="empty-state">
              <div class="placeholder-text">请选择拓扑节点</div>
              <div class="placeholder-desc">点击左侧拓扑树节点查看节点信息</div>
            </div>
            <node-info-panel v-else :node="selectedNode"></node-info-panel>
          </bk-tab-panel>
        </bk-tab>
      </div>
    </div>
  </div>
</template>

<script>
import TopologyTree from './topology-tree.vue'
import HostListPanel from './host-list-panel.vue'
import NodeInfoPanel from './node-info-panel.vue'

export default {
  name: 'BusinessTopology',
  components: {
    TopologyTree,
    HostListPanel,
    NodeInfoPanel
  },
  data() {
    return {
      leftWidth: 280,
      leftCollapsed: false,
      isResizing: false,
      startX: 0,
      startWidth: 0,
      minWidth: 200,
      maxWidth: 480,
      activeTab: 'hostList',
      selectedNode: null
    }
  },
  methods: {
    toggleLeftPanel() {
      this.leftCollapsed = !this.leftCollapsed
    },
    handleResizeStart(event) {
      if (this.leftCollapsed) return
      this.isResizing = true
      this.startX = event.clientX
      this.startWidth = this.leftWidth
      document.addEventListener('mousemove', this.handleResizeMove)
      document.addEventListener('mouseup', this.handleResizeEnd)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    },
    handleResizeMove(event) {
      if (!this.isResizing) return
      const deltaX = this.startX - event.clientX
      let newWidth = this.startWidth + deltaX
      if (newWidth < this.minWidth) {
        newWidth = this.minWidth
      }
      if (newWidth > this.maxWidth) {
        newWidth = this.maxWidth
      }
      this.leftWidth = newWidth
    },
    handleResizeEnd() {
      this.isResizing = false
      document.removeEventListener('mousemove', this.handleResizeMove)
      document.removeEventListener('mouseup', this.handleResizeEnd)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    },
    handleNodeSelect(node) {
      this.selectedNode = node
    }
  },
  beforeDestroy() {
    document.removeEventListener('mousemove', this.handleResizeMove)
    document.removeEventListener('mouseup', this.handleResizeEnd)
  }
}
</script>

<style lang="scss" scoped>
.business-topology {
  height: 100%;
  width: 100%;
  overflow: hidden;
  background: #fff;
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
  overflow: hidden;
}

.left-panel {
  flex-shrink: 0;
  border-right: 1px solid $cmdbLayoutBorderColor;
  transition: width 0.2s ease;

  &.is-collapsed {
    width: 0 !important;
    border-right: none;
    overflow: hidden;
  }
}

.right-panel {
  flex: 1;
  min-width: 0;

  .topology-tab {
    height: 100%;

    ::v-deep .bk-tab-header {
      padding: 0;
      margin: 0 20px;
    }

    ::v-deep .bk-tab-section {
      height: calc(100% - 50px);
      overflow: auto;
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

.resize-handler {
  width: 6px;
  flex-shrink: 0;
  height: 100%;
  cursor: col-resize;
  position: relative;
  background: transparent;
  transition: background-color 0.2s;
  z-index: 10;

  &:hover {
    background: rgba(58, 132, 255, 0.1);
  }

  &.is-collapsed {
    cursor: default;

    &:hover {
      background: transparent;
    }
  }

  .collapse-icon {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 16px;
    height: 60px;
    line-height: 60px;
    text-align: center;
    background: $cmdbLayoutBorderColor;
    border-radius: 0 8px 8px 0;
    color: #fff;
    font-size: 14px;
    cursor: pointer;
    transition: background-color 0.2s;

    &:hover {
      background: $primaryColor;
    }
  }
}
</style>