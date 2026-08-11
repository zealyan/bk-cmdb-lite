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
      <span class="info-item info-user"
        v-if="userName">
        <span class="user-name">{{ userName }}</span>
        <i class="user-icon bk-icon icon-angle-down"></i>
        <div class="user-dropdown">
          <a class="link-item" href="javascript:void(0)" @click.prevent="handleLogout">
            <i class="link-icon bk-icon icon-cc-logout"></i>注销
          </a>
        </div>
      </span>
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
import { me, logout } from '@/api/auth'
import { clearToken, getUserName, setUserName } from '@/auth'

export default {
  name: 'CmdbHeader',
  data() {
    return {
      MENU_RESOURCE_MANAGEMENT,
      MENU_MODEL_MANAGEMENT
    }
  },
  created() {
    this.loadUser()
  },
  computed: {
    headerMenus() {
      return menu
    },
    // 登录用户名来自全应用共享 store（common 显示），不受路由页面影响
    userName() {
      return this.$store.getters['user/userName']
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
    },
    /**
     * 拉取当前登录用户名：优先 localStorage（登录时已写），再回源 /me。
     * 免登录模式下 /me 返回 skipLogin:true + bk_user_name:admin，页头显示 admin。
     */
    async loadUser() {
      const cached = getUserName()
      if (cached) this.$store.commit('user/setUser', { name: cached })
      try {
        const info = await me()
        const name = info && info.bk_user_name
        if (name) {
          this.$store.commit('user/setUser', { name, skipLogin: info.skipLogin })
          setUserName(name)
        } else if (!this.userName) {
          this.$store.commit('user/setUser', { name: 'admin' })
        }
      } catch (e) {
        if (!this.userName) this.$store.commit('user/setUser', { name: 'admin' })
      }
    },
    /**
     * 注销：调后端 logout（无状态 token，前端清 localStorage 即失效），
     * 清 token + 共享 store 登录态后跳登录页；路由守卫重新判定登录态。
     */
    async handleLogout() {
      try {
        await logout()
      } catch (e) {
        // 后端无状态，失败也不阻塞前端清理
      }
      clearToken()
      this.$store.commit('user/clearUser')
      this.$router.replace({ path: '/login' })
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
  display: flex;
  align-items: center;
  justify-content: flex-end;
  text-align: right;
  white-space: nowrap;
  font-size: 0;
  height: 58px;
  padding-right: 16px;
}

.info-item {
  font-size: 0;
  cursor: pointer;
}

.info-user {
  position: relative;
  display: inline-flex;
  align-items: center;
  height: 32px;
  padding: 0 6px;
  font-size: 14px;
  font-weight: 600;
  color: #c2cee5;
  border-radius: 2px;
  transition: background-color .2s, color .2s;

  .user-name {
    max-width: 160px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .user-icon {
    margin-left: 2px;
    font-size: 18px;
    color: #8a94a6;
    transition: transform .2s linear, color .2s;
  }

  &:hover {
    color: #fff;
    background-color: rgba(49, 64, 94, 0.5);

    .user-icon {
      color: #fff;
      transform: rotate(180deg);
    }

    .user-dropdown {
      opacity: 1;
      visibility: visible;
      transform: translateY(0);
    }
  }
}

.user-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 6px;
  min-width: 116px;
  padding: 4px 0;
  background: #fff;
  border-radius: 2px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, .18);
  opacity: 0;
  visibility: hidden;
  transform: translateY(-6px);
  transition: opacity .2s, transform .2s, visibility .2s;
  z-index: 2000;

  .link-item {
    display: flex;
    align-items: center;
    height: 40px;
    padding: 0 20px;
    font-size: 14px;
    line-height: normal;
    color: #313238;
    text-decoration: none;
    white-space: nowrap;

    .link-icon {
      margin-right: 6px;
      font-size: 14px;
    }

    &:hover {
      background-color: #f1f7ff;
      color: #3a84ff;
    }
  }
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
