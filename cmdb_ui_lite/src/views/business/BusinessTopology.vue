<template>
  <div class="business-topology">
    <div class="topology-layout">
      <div class="left-panel">
        <div class="panel-header">
          <span class="panel-title">拓扑树</span>
        </div>
        <div class="panel-content">
          <div class="placeholder-text">左侧菜单 - 拓扑树占位</div>
          <div class="placeholder-desc">待开发：业务拓扑树结构</div>
        </div>
      </div>

      <div
        class="resize-handler"
        :class="{ 'is-collapsed': middleCollapsed }"
        @mousedown="handleResizeStart"
        @dblclick="toggleMiddlePanel">
        <i
          class="collapse-icon bk-icon"
          :class="middleCollapsed ? 'icon-angle-right' : 'icon-angle-left'"
          @click.stop="toggleMiddlePanel">
        </i>
      </div>

      <div
        class="middle-panel"
        :class="{ 'is-collapsed': middleCollapsed }"
        :style="{ width: middleWidth + 'px' }">
        <div class="panel-header">
          <span class="panel-title">实例列表</span>
        </div>
        <div class="panel-content">
          <div class="placeholder-text">中栏 - 实例列表占位</div>
          <div class="placeholder-desc">待开发：主机/服务实例列表</div>
        </div>
      </div>

      <div class="right-panel">
        <div class="panel-header">
          <span class="panel-title">详情信息</span>
        </div>
        <div class="panel-content">
          <div class="placeholder-text">右侧栏 - 详情信息占位</div>
          <div class="placeholder-desc">待开发：节点详情/属性信息</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'BusinessTopology',
  data() {
    return {
      middleWidth: 400,
      middleCollapsed: false,
      isResizing: false,
      startX: 0,
      startWidth: 0,
      minWidth: 200,
      maxWidth: 600
    }
  },
  methods: {
    toggleMiddlePanel() {
      this.middleCollapsed = !this.middleCollapsed
    },
    handleResizeStart(event) {
      if (this.middleCollapsed) return
      this.isResizing = true
      this.startX = event.clientX
      this.startWidth = this.middleWidth
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
      this.middleWidth = newWidth
    },
    handleResizeEnd() {
      this.isResizing = false
      document.removeEventListener('mousemove', this.handleResizeMove)
      document.removeEventListener('mouseup', this.handleResizeEnd)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
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
.middle-panel,
.right-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.left-panel {
  width: 280px;
  flex-shrink: 0;
  border-right: 1px solid $cmdbLayoutBorderColor;
}

.middle-panel {
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
}

.panel-header {
  height: 48px;
  line-height: 48px;
  padding: 0 16px;
  border-bottom: 1px solid $cmdbLayoutBorderColor;
  background: #fafbfc;
  flex-shrink: 0;

  .panel-title {
    font-size: 14px;
    font-weight: 500;
    color: $cmdbTextColor;
  }
}

.panel-content {
  flex: 1;
  overflow: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.placeholder-text {
  font-size: 16px;
  color: $grayColor;
  margin-bottom: 8px;
}

.placeholder-desc {
  font-size: 12px;
  color: $textDisabledColor;
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
