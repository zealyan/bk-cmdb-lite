<template>
  <div class="clearfix">
    <dynamic-navigation class="main-navigation" v-show="!isEntry"></dynamic-navigation>
    <dynamic-breadcrumbs class="main-breadcrumbs" ref="breadcrumbs" v-if="showBreadcrumbs"></dynamic-breadcrumbs>
    <div class="main-layout">
      <div class="main-scroller" ref="scroller">
        <router-view class="main-views" :name="view" ref="view"></router-view>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'
import dynamicNavigation from './dynamic-navigation'
import dynamicBreadcrumbs from './dynamic-breadcrumbs'
import { MENU_ENTRY } from '@/dictionary/menu-symbol'

export default {
  name: 'DynamicRouterView',
  components: {
    dynamicNavigation,
    dynamicBreadcrumbs
  },
  data() {
    return {
      meta: this.$route.meta
    }
  },
  computed: {
    ...mapGetters(['globalLoading']),
    view() {
      return this.meta.view || 'default'
    },
    isEntry() {
      const [topRoute] = this.$route.matched
      return topRoute && topRoute.name === MENU_ENTRY
    },
    showBreadcrumbs() {
      return this.$route.meta.layout && this.$route.meta.layout.breadcrumbs
    }
  },
  watch: {
    $route() {
      this.meta = this.$route.meta
    }
  },
  mounted() {
    this.updateScrollerState()
    this.$refs.scroller.addEventListener('scroll', this.handleScroll)
  },
  beforeDestroy() {
    if (this.$refs.scroller) {
      this.$refs.scroller.removeEventListener('scroll', this.handleScroll)
    }
  },
  methods: {
    handleScroll() {
      this.updateScrollerState()
    },
    updateScrollerState() {
      const { scroller } = this.$refs
      if (scroller) {
        this.$store.commit('setScrollerState', {
          scrollbar: scroller.scrollHeight > scroller.offsetHeight
        })
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.main-navigation {
  float: left;
}

.main-breadcrumbs {
  overflow: hidden;
  position: relative;
  background-color: #fff;
  z-index: 100;
}

.main-layout {
  position: relative;
  overflow: hidden;
  height: calc(100% - 53px);
  z-index: 99;
}

.main-scroller {
  height: 100%;
  overflow: auto;
}

.main-views {
  position: relative;
  height: 100%;
  min-width: 1089px;
}

.clearfix::after {
  content: '';
  display: table;
  clear: both;
}
</style>
