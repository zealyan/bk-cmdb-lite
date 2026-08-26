<template>
  <!--
    首页占位模板（index）。
    对齐原项目 bk-cmdb/src/ui/src/views/index/index.vue 的路由入口：
      - 路由名：MENU_INDEX（menu_index）
      - 路径：/index
      - 菜单 i18n：首页
      - 面包屑：关闭（layout.breadcrumbs = false）
    当前仅保留「首页容器骨架」，暂不实现原项目内部内容（主机搜索 / 全文检索 / 地图 / 页脚等）。
    后续接入时，可参照原项目 ./children 下的 host-search、full-text-search、map、footer 等子组件逐步补齐。
  -->
  <div class="index-layout">
    <div class="index-placeholder">
      <i class="index-placeholder-icon bk-icon icon-cc-home"></i>
      <h1 class="index-placeholder-title">首页</h1>
      <p class="index-placeholder-desc">由顶部导航栏开始你的旅途</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'cmdbIndex'
}
</script>

<style lang="scss" scoped>
.index-layout {
  height: 100%;
  background-color: #f5f6fa;
  display: flex;
  align-items: center;
  justify-content: center;
}

.index-placeholder {
  text-align: center;
  color: #63656e;
  user-select: none;

  .index-placeholder-icon {
    display: block;
    font-size: 56px;
    line-height: 1;
    color: #c4c6cc;
  }

  .index-placeholder-title {
    margin: 20px 0 8px;
    font-size: 20px;
    font-weight: 600;
    color: #313238;
  }

  .index-placeholder-desc {
    margin: 0;
    font-size: 14px;
    color: #979ba5;
  }
}
</style>
