<template>
  <div class="node-info-panel">
    <div class="info-header">
      <span class="node-icon">{{ nodeIconText }}</span>
      <span class="node-name">{{ node.data.bk_inst_name }}</span>
      <span class="node-type-tag">{{ node.data.bk_obj_name }}</span>
    </div>
    <div class="info-body">
      <div class="info-section">
        <h4 class="section-title">基本信息</h4>
        <div class="info-item">
          <span class="info-label">节点类型:</span>
          <span class="info-value">{{ node.data.bk_obj_name }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">节点ID:</span>
          <span class="info-value">{{ node.data.bk_inst_id }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">节点名称:</span>
          <span class="info-value">{{ node.data.bk_inst_name }}</span>
        </div>
        <div class="info-item" v-if="node.data.default !== 0 && node.data.default !== undefined">
          <span class="info-label">节点属性:</span>
          <span class="info-value">{{ node.data.default === 1 ? '空闲机' : '故障机' }}</span>
        </div>
      </div>
      <div class="info-section">
        <h4 class="section-title">统计信息</h4>
        <div class="info-item">
          <span class="info-label">主机数量:</span>
          <span class="info-value">{{ node.data.host_count || 0 }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">服务实例数量:</span>
          <span class="info-value">{{ node.data.service_instance_count || 0 }}</span>
        </div>
      </div>
      <div class="info-section" v-if="nodePath.length > 1">
        <h4 class="section-title">拓扑路径</h4>
        <div class="path-list">
          <div class="path-item" v-for="(name, index) in nodePath" :key="index">
            <span class="path-icon" v-if="index > 0">/</span>
            <span class="path-name">{{ name }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'NodeInfoPanel',
  props: {
    node: {
      type: Object,
      required: true
    }
  },
  computed: {
    nodeIconText() {
      return this.node.data.icon_text || this.node.data.bk_obj_name?.[0] || 'N'
    },
    nodePath() {
      let path = []
      let current = this.node
      while (current) {
        path.unshift(current.data.bk_inst_name)
        current = current.parent
      }
      return path
    }
  }
}
</script>

<style lang="scss" scoped>
.node-info-panel {
  padding: 20px;
}

.info-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid $cmdbLayoutBorderColor;

  .node-icon {
    display: inline-flex;
    width: 32px;
    height: 32px;
    line-height: 32px;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background-color: #c4c6cc;
    font-size: 14px;
    color: #fff;
    margin-right: 12px;
  }

  .node-name {
    font-size: 18px;
    font-weight: 500;
    color: $cmdbTextColor;
    flex: 1;
  }

  .node-type-tag {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 4px;
    background-color: #f0f1f5;
    color: #63656e;
    font-size: 12px;
  }
}

.info-body {
  .info-section {
    margin-bottom: 24px;

    &:last-child {
      margin-bottom: 0;
    }

    .section-title {
      font-size: 14px;
      font-weight: 500;
      color: $cmdbTextColor;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid $cmdbLayoutBorderColor;
    }

    .info-item {
      display: flex;
      margin-bottom: 8px;

      &:last-child {
        margin-bottom: 0;
      }

      .info-label {
        width: 120px;
        color: $grayColor;
        font-size: 14px;
      }

      .info-value {
        flex: 1;
        color: $cmdbTextColor;
        font-size: 14px;
      }
    }
  }

  .path-list {
    display: flex;
    flex-wrap: wrap;
    align-items: center;

    .path-item {
      display: flex;
      align-items: center;

      .path-icon {
        margin: 0 8px;
        color: $grayColor;
      }

      .path-name {
        color: $cmdbTextColor;
        font-size: 14px;

        &:hover {
          color: $primaryColor;
        }
      }
    }
  }
}
</style>