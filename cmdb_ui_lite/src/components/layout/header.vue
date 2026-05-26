<template>
  <div class="cmdb-navigation">
    <div class="navigation-header">
      <div class="header-logo">
        <span class="logo-icon bk-icon icon-cc-home"></span>
        <span class="logo-text">CMDB</span>
      </div>
      <nav class="header-nav">
        <router-link to="/resource/index">资源</router-link>
      </nav>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CmdbHeader'
}
</script>

<style lang="scss" scoped>
.cmdb-navigation {
  height: 52px;
  background: #1a1a1a;
  flex-shrink: 0;
}

.navigation-header {
  height: 100%;
  display: flex;
  align-items: center;
  padding: 0 24px;
}

.header-logo {
  display: flex;
  align-items: center;
  margin-right: 40px;

  .logo-icon {
    font-size: 20px;
    margin-right: 8px;
  }

  .logo-text {
    font-weight: 700;
    font-size: 16px;
    color: #fff;
  }
}

.header-nav {
  display: flex;
  gap: 8px;

  a {
    color: rgba(255, 255, 255, 0.65);
    text-decoration: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 14px;
    transition: all 0.2s;

    &:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.1);
    }

    &.router-link-active {
      color: #fff;
      background: #175ee5;
    }
  }
}
</style>
