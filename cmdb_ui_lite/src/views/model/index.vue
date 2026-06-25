<template>
  <div class="model-manage-page">
    <div class="page-header">
      <h2>模型管理</h2>
    </div>
    <div class="page-content">
      <div class="empty-state">
        <i class="bk-icon icon-cc-nav-model-02"></i>
        <p>模型管理功能开发中...</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ModelManagement'
}
</script>

<style lang="scss" scoped>
.model-manage-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;

  h2 {
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    margin: 0;
  }
}

.page-content {
  min-height: 200px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: #979ba5;

  .bk-icon {
    font-size: 64px;
    margin-bottom: 16px;
    color: #c4c6cc;
  }

  p {
    font-size: 14px;
    margin: 0;
  }
}
</style>
