<template>
  <nav class="nav-layout"
    :class="{ 'sticked': navStick }"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave">
    <div class="nav-wrapper"
      :class="{ unfold: unfold, flexible: !navStick }">
      <!-- 业务选择器（仅业务视图显示） -->
      <div class="business-wrapper" v-if="isBusinessView">
        <transition name="fade">
          <div class="business-selector" v-show="unfold">
            <bk-select
              v-model="selectedBizId"
              :loading="bizLoading"
              :searchable="true"
              :clearable="false"
              placeholder="请选择业务"
              popover-width="240"
              ext-popover-cls="biz-selector-dropdown"
              @selected="handleBizChange">
              <bk-option
                v-for="biz in bizList"
                :key="biz.bk_biz_id"
                :id="String(biz.bk_biz_id)"
                :name="`${biz.bk_biz_name}(${biz.bk_biz_id})`">
                <div class="biz-option-item">
                  <span class="biz-name">{{ biz.bk_biz_name }}</span>
                  <span class="biz-id">({{ biz.bk_biz_id }})</span>
                </div>
              </bk-option>
            </bk-select>
          </div>
        </transition>
        <transition name="fade">
          <i class="business-flag bk-icon icon-angle-down" v-show="!unfold"
            v-bk-tooltips.right="currentBizName"></i>
        </transition>
      </div>
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
import {
  MENU_BUSINESS,
  MENU_RESOURCE,
  MENU_MODEL,
  MENU_RESOURCE_INSTANCE,
  MENU_BUSINESS_TOPOLOGY
} from '@/dictionary/menu-symbol'
import { modelAPI } from '@/api/client'
import { getCachedBizId } from '@/utils/biz-cache'

export default {
  name: 'DynamicNavigation',
  data() {
    return {
      timer: null,
      bizList: [],
      bizLoading: false,
      selectedBizId: ''
    }
  },
  computed: {
    ...mapGetters(['navStick', 'navFold']),
    ...mapGetters('userCustom', ['resourceCollection']),
    ...mapGetters('objectModelClassify', ['models']),
    unfold() {
      return this.navStick || !this.navFold
    },
    isBusinessView() {
      const [topRoute] = this.$route.matched
      return topRoute?.name === MENU_BUSINESS
    },
    currentBizId() {
      const bizId = this.$route.params.bizId
      return bizId ? String(bizId) : ''
    },
    currentBizName() {
      const biz = this.bizList.find(b => String(b.bk_biz_id) === this.currentBizId)
      return biz ? biz.bk_biz_name : ''
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
      let menus = [...((target && target.menu) || [])]
      if (this.owner === MENU_BUSINESS) {
        menus = menus.map(menu => {
          if (menu.id === MENU_BUSINESS_TOPOLOGY) {
            // 对齐原项目 getMenuLink：菜单链接的 bizId 取自 store 的 objectBiz/bizId
            // （由路由守卫在进入业务时绑定），缺失时回退到全局默认缓存的业务 ID，
            // 保证菜单链接本身指向一个合法业务，而非 /business/0/index
            const storeBizId = this.$store.getters['objectBiz/bizId']
            const effectiveBizId = (storeBizId && String(storeBizId) !== '0')
              ? String(storeBizId)
              : getCachedBizId()
            return {
              ...menu,
              route: {
                name: MENU_BUSINESS_TOPOLOGY,
                params: {
                  bizId: effectiveBizId
                }
              }
            }
          }
          return menu
        })
      }
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
    },
    async loadBizList() {
      if (this.bizList.length > 0) return
      this.bizLoading = true
      try {
        const res = await modelAPI.getBizList()
        if (res) {
          this.bizList = res.filter(b => b.default !== 1)
        }
      } catch (e) {
        console.error('[DynamicNavigation] 加载业务列表失败:', e)
      } finally {
        this.bizLoading = false
      }
    },
    handleBizChange(value) {
      if (!value) return
      const targetBizId = value
      // 保存与数据绑定由路由守卫（beforeEach）在进入目标业务路由时统一处理，
      // 这里仅负责导航到目标业务（守卫会写入 localStorage['selectedBusiness'] 并提交 store）
      const currentPath = this.$route.path
      const bizIdPattern = /^\/business\/(\d+)(\/.*)?$/
      if (bizIdPattern.test(currentPath)) {
        const newPath = currentPath.replace(bizIdPattern, `/business/${targetBizId}$2`)
        this.$router.replace(newPath)
      } else {
        this.$router.push({
          name: MENU_BUSINESS_TOPOLOGY,
          params: { bizId: targetBizId }
        })
      }
    },
    syncSelectedBiz() {
      if (this.isBusinessView && this.currentBizId && this.currentBizId !== '0') {
        // 选择器默认选中当前业务：优先取 store 中由守卫绑定的 objectBiz/bizId，
        // 与导航栏菜单链接、业务内容保持一致（原项目的数据绑定方式）
        const storeBizId = this.$store.getters['objectBiz/bizId']
        this.selectedBizId = (storeBizId && String(storeBizId) !== '0')
          ? String(storeBizId)
          : this.currentBizId
      }
    }
  },
  watch: {
    isBusinessView: {
      immediate: true,
      handler(val) {
        if (val) {
          this.loadBizList()
        }
      }
    },
    '$route': {
      immediate: true,
      handler() {
        this.syncSelectedBiz()
      }
    },
    // 业务列表异步加载完成后，重新同步选择器默认选中，
    // 避免「路由已就绪但选项尚未渲染」导致下拉框显示为空
    bizList() {
      this.syncSelectedBiz()
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

.business-wrapper {
  border-bottom: 1px solid #DCDEE5;

  .business-selector {
    width: 100%;
    padding: 10px 16px;

    .bk-select {
      width: 100%;
    }
  }

  .business-flag {
    display: block;
    width: 100%;
    padding: 10px 0;
    text-align: center;
    font-size: 16px;
    color: #979BA5;
    cursor: pointer;
    line-height: 20px;
  }
}

.biz-option-item {
  display: flex;
  align-items: center;
  justify-content: space-between;

  .biz-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .biz-id {
    color: #979BA5;
    font-size: 12px;
    margin-left: 8px;
    flex-shrink: 0;
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
