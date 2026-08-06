<template>
  <header class="header-layout" :class="{ 'nav-compact': isCompactNav }">
    <div class="logo">
      <router-link class="logo-link" :to="{ name: MENU_RESOURCE_MANAGEMENT }">
        <span class="logo-icon bk-icon icon-cc-cmdb"></span>
        <span class="logo-text">配置平台</span>
      </router-link>
    </div>
    <nav class="header-nav">
      <router-link
        class="header-link"
        v-for="nav in headerMenus"
        :to="getHeaderLink(nav)"
        :key="nav.id"
        :class="{ active: isLinkActive(nav) }">
        {{ nav.i18n }}
      </router-link>
    </nav>
    <section class="header-info">
    </section>
  </header>
</template>

<script>
import menu from '@/dictionary/menu'
import {
  MENU_BUSINESS,
  MENU_BUSINESS_TOPOLOGY,
  MENU_RESOURCE,
  MENU_MODEL,
  MENU_RESOURCE_MANAGEMENT,
  MENU_MODEL_MANAGEMENT
} from '@/dictionary/menu-symbol'
import { getCachedBizId } from '@/utils/biz-cache'

export default {
  name: 'CmdbHeader',
  data() {
    return {
      MENU_RESOURCE_MANAGEMENT,
      MENU_MODEL_MANAGEMENT
    }
  },
  computed: {
    headerMenus() {
      return menu
    },
    isCompactNav() {
      const firstMenuId = this.headerMenus[0]?.id
      const secondMenuId = this.headerMenus[1]?.id
      const hasHomeOrBiz = firstMenuId === 'menu_index' || firstMenuId === 'menu_business'
        || secondMenuId === 'menu_index' || secondMenuId === 'menu_business'
      return !hasHomeOrBiz
    }
  },
  methods: {
    isLinkActive(nav) {
      const [topRoute] = this.$route.matched
      if (!topRoute) {
        return false
      }
      return topRoute.name === nav.id
    },
    getHeaderLink(nav) {
      // 对齐原项目 header.getHeaderLink：顶栏「业务」标签回到缓存/选中的业务
      // （objectBiz/bizId，由路由守卫在进入业务时绑定），而非写死的固定 bizId
      if (nav.id === MENU_BUSINESS) {
        const storeBizId = this.$store.getters['objectBiz/bizId']
        const bizId = (storeBizId && String(storeBizId) !== '0') ? String(storeBizId) : getCachedBizId()
        return { name: MENU_BUSINESS_TOPOLOGY, params: { bizId } }
      }
      const firstChild = nav.menu && nav.menu[0]
      if (firstChild && firstChild.route) {
        return firstChild.route
      }
      return { name: nav.id }
    }
  }
}
</script>

<style lang="scss" scoped>
.header-layout {
  position: relative;
  display: flex;
  height: 58px;
  background-color: #182132;
  z-index: 1002;
  flex-shrink: 0;
}

.logo {
  flex: 130px 0 0;
  font-size: 0;

  .logo-link {
    display: inline-flex;
    align-items: center;
    height: 58px;
    margin-left: 24px;
    color: #fff;
    font-size: 16px;
    text-decoration: none;

    .logo-icon {
      font-size: 24px;
      margin-right: 10px;
      color: #3a84ff;
    }

    .logo-text {
      font-weight: 500;
      font-size: 16px;
      color: #fff;
      letter-spacing: 1px;
    }
  }
}

.header-nav {
  flex: 3;
  font-size: 0;
  white-space: nowrap;

  .header-link {
    display: inline-block;
    vertical-align: middle;
    height: 58px;
    line-height: 58px;
    padding: 0 25px;
    color: #96A2B9;
    font-size: 14px;
    text-decoration: none;
    transition: all 0.2s;

    &:hover {
      background-color: rgba(49, 64, 94, 0.5);
      color: #C2CEE5;
    }

    &.router-link-active,
    &.active {
      background-color: rgba(49, 64, 94, 1);
      color: #fff;
    }
  }
}

.header-info {
  flex: 1;
  text-align: right;
  white-space: nowrap;
  font-size: 0;
}

.nav-compact {
  .logo {
    flex: 0 0 auto;
    padding-right: 16px;

    .logo-link {
      margin-left: 24px;
    }
  }

  .header-nav {
    flex: 0 0 auto;
  }

  .header-info {
    flex: 1;
  }
}
</style>
