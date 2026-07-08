<template>
  <nav class="nav-layout"
    :class="{ 'sticked': navStick }"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave">
    <div class="nav-wrapper"
      :class="{ unfold: unfold, flexible: !navStick }">
      <div class="menu-list">
        <template v-for="(menu, index) in currentMenus">
          <router-link
            :key="index"
            tag="a"
            active-class="active"
            style="display: block;"
            v-if="menu.hasOwnProperty('route')"
            :class="['menu-item', 'is-link']"
            :to="menu.route"
            :title="menu.i18n">
            <h3 class="menu-info clearfix">
              <i :class="['menu-icon', menu.icon]"></i>
              <span class="menu-name">{{ menu.i18n }}</span>
            </h3>
          </router-link>
        </template>
      </div>
      <div class="nav-option">
        <i class="nav-stick icon icon-cc-nav-toggle"
          :class="{
            sticked: navStick
          }"
          :title="navStick ? '收起导航' : '固定导航'"
          @click="toggleNavStick">
        </i>
      </div>
    </div>
  </nav>
</template>

<script>
import { mapGetters, mapActions } from 'vuex'
import MENU_DICTIONARY from '@/dictionary/menu'
import { MENU_BUSINESS, MENU_RESOURCE, MENU_MODEL, MENU_RESOURCE_INSTANCE } from '@/dictionary/menu-symbol'

export default {
  name: 'DynamicNavigation',
  data() {
    return {
      timer: null
    }
  },
  computed: {
    ...mapGetters(['navStick', 'navFold']),
    ...mapGetters('userCustom', ['resourceCollection']),
    ...mapGetters('objectModelClassify', ['models']),
    unfold() {
      return this.navStick || !this.navFold
    },
    owner() {
      const [topRoute] = this.$route.matched
      return topRoute?.name || MENU_BUSINESS
    },
    collectionMenus() {
      return this.resourceCollection.map((id) => {
        const model = this.models.find(m => m.bk_obj_id === id)
        return {
          id: `collection_${id}`,
          i18n: model?.bk_obj_name || id,
          icon: model?.bk_obj_icon || 'icon-cc-default',
          route: {
            name: MENU_RESOURCE_INSTANCE,
            params: {
              objId: id
            }
          }
        }
      })
    },
    currentMenus() {
      const target = MENU_DICTIONARY.find(menu => menu.id === this.owner)
      const menus = [...((target && target.menu) || [])]
      if (this.owner === MENU_RESOURCE && this.collectionMenus.length > 0) {
        menus.splice(1, 0, ...this.collectionMenus)
      }
      return menus
    }
  },
  methods: {
    ...mapActions('userCustom', ['searchUsercustom']),
    handleMouseEnter() {
      if (this.timer) {
        clearTimeout(this.timer)
      }
      this.$store.commit('setNavStatus', { fold: false })
    },
    handleMouseLeave() {
      this.timer = setTimeout(() => {
        this.$store.commit('setNavStatus', { fold: true })
      }, 300)
    },
    toggleNavStick() {
      this.$store.commit('setNavStatus', {
        fold: !this.navFold,
        stick: !this.navStick
      })
    }
  },
  async mounted() {
    try {
      await this.searchUsercustom()
    } catch (e) {
      console.error('[DynamicNavigation] 加载用户配置失败:', e)
    }
  }
}
</script>

<style lang="scss" scoped>
$cubicBezier: cubic-bezier(0.4, 0, 0.2, 1);
$duration: 0.2s;
$color: #63656E;

.nav-layout {
  position: relative;
  width: 60px;
  height: 100%;
  transition: width $duration $cubicBezier;
  z-index: 1000;

  &.sticked {
    width: 260px;
  }

  .nav-wrapper {
    position: relative;
    width: 100%;
    height: 100%;
    border-right: 1px solid #DCDEE5;
    background: #fff;
    transition: width $duration $cubicBezier;

    &.unfold {
      width: 260px;
    }

    &.unfold.flexible:after {
      content: "";
      position: absolute;
      width: 15px;
      height: 100%;
      left: 100%;
      top: 0;
    }
  }
}

.menu-list {
  padding: 10px 0;
  height: calc(100% - 60px);
  overflow-y: auto;
  overflow-x: hidden;
  white-space: nowrap;

  &::-webkit-scrollbar {
    width: 5px;
    height: 5px;

    &-thumb {
      border-radius: 20px;
      background: rgba(165, 165, 165, .3);
      box-shadow: inset 0 0 6px hsla(0, 0%, 80%, .3);
    }
  }

  .menu-item {
    position: relative;

    &:hover {
      background-color: #F6F6F9;
    }

    &.active.is-link {
      background-color: #E1ECFF;

      .menu-icon,
      .menu-name {
        color: $primaryColor;
      }
    }

    .menu-info {
      margin: 0;
      padding: 0;
      height: 42px;
      line-height: 42px;
      white-space: nowrap;
      font-size: 0;
      font-weight: normal;
      color: $color;
      cursor: pointer;
    }

    .menu-icon {
      display: inline-block;
      vertical-align: top;
      margin: 13px 26px 13px 22px;
      font-size: 16px;
      color: #979BA5;
    }

    .menu-name {
      display: inline-block;
      width: calc(100% - 120px);
      vertical-align: top;
      font-size: 14px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}

.nav-option {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 50px;
  line-height: 49px;
  border-top: 1px solid #DCDEE5;
  font-size: 0;
  color: #63656E;

  &:before {
    content: "";
    display: inline-block;
    height: 100%;
    width: 0;
    vertical-align: middle;
  }

  .nav-stick {
    display: inline-block;
    vertical-align: middle;
    width: 32px;
    height: 32px;
    margin: 0 0 0 13px;
    line-height: 32px;
    text-align: center;
    font-size: 14px;
    cursor: pointer;
    transition: transform $duration $cubicBezier;

    &:hover {
      opacity: .8;
    }

    &.sticked {
      transform: rotate(180deg);
    }
  }
}
</style>
