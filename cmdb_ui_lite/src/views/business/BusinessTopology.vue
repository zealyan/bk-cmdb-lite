<template>
  <div class="business-topology">
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

        <!-- resize 分隔条和折叠图标（始终显示） -->
        <div
          class="resize-handler"
          @mousedown.left="handleResizeStart"
          @dblclick="toggleLeftPanel">
          <i
            class="topology-collapse-icon bk-icon icon-angle-left"
            @click.stop="toggleLeftPanel">
          </i>
        </div>
      </div>

      <!-- resize 代理虚线（相对于 topology-layout 定位） -->
      <i class="resize-proxy" ref="resizeProxy"></i>
      <!-- resize 遮罩 -->
      <div class="resize-mask" ref="resizeMask"></div>

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
      resizeState: {},
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
      const $handler = event.currentTarget
      const $layout = this.$refs.topologyLayout
      const layoutRect = $layout.getBoundingClientRect()
      const $resizeProxy = this.$refs.resizeProxy
      const $resizeMask = this.$refs.resizeMask

      // 显示代理线和遮罩
      $resizeProxy.style.visibility = 'visible'
      $resizeMask.style.display = 'block'

      // handler 右边相对于 layout 左边的距离 = 面板右边位置
      const handlerRight = $handler.getBoundingClientRect().right - layoutRect.left

      // 记录初始状态（都是相对于 layout 容器的坐标）
      this.resizeState = {
        startMouseLeft: event.clientX - layoutRect.left,
        startLeft: handlerRight
      }

      // 设置代理线位置（相对于 layout）
      $resizeProxy.style.top = '0'
      $resizeProxy.style.left = `${this.resizeState.startLeft}px`
      $resizeProxy.style.height = '100%'
      $resizeMask.style.cursor = 'col-resize'

      // 禁止文本选择和拖拽
      document.onselectstart = () => false
      document.ondragstart = () => false

      // 绑定鼠标移动和松开事件
      document.addEventListener('mousemove', this.handleResizeMove)
      document.addEventListener('mouseup', this.handleResizeEnd)
    },
    handleResizeMove(event) {
      const $resizeProxy = this.$refs.resizeProxy
      const $layout = this.$refs.topologyLayout
      const layoutRect = $layout.getBoundingClientRect()

      // 鼠标位置相对于 layout 左边
      const mouseLeft = event.clientX - layoutRect.left
      // 向右拖动为正，增加宽度
      const deltaLeft = mouseLeft - this.resizeState.startMouseLeft
      const proxyLeft = this.resizeState.startLeft + deltaLeft
      // 限制在 min/max 范围内
      const clampedLeft = Math.min(this.maxWidth, Math.max(this.minWidth, proxyLeft))
      $resizeProxy.style.left = `${clampedLeft}px`
    },
    handleResizeEnd() {
      const $resizeProxy = this.$refs.resizeProxy
      const $resizeMask = this.$refs.resizeMask

      // 获取最终位置并设置宽度
      const finalLeft = parseInt($resizeProxy.style.left, 10)
      this.leftWidth = finalLeft

      // 隐藏代理线和遮罩
      $resizeProxy.style.visibility = 'hidden'
      $resizeMask.style.display = 'none'

      // 移除事件监听
      document.removeEventListener('mousemove', this.handleResizeMove)
      document.removeEventListener('mouseup', this.handleResizeEnd)
      document.onselectstart = null
      document.ondragstart = null
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

.left-panel {
  position: relative;

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

    .topology-collapse-icon {
      position: absolute;
      left: 0;
      top: 50%;
      width: 16px;
      height: 100px;
      line-height: 100px;
      background: $cmdbLayoutBorderColor;
      border-radius: 0px 12px 12px 0px;
      transform: translateY(-50%);
      text-align: center;
      font-size: 20px;
      color: #fff;
      cursor: pointer;
      text-indent: -2px;
      transition: background-color 0.2s;

      &:hover {
        background: #699DF4;
      }
    }
  }

  &.is-collapsed {
    width: 0 !important;
    border-right: none;
    overflow: visible;

    .topology-collapse-icon:before {
      display: inline-block;
      transform: rotate(180deg);
    }
  }
}

.expand-btn {
  display: none;
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
</style>