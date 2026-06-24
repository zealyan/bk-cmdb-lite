<template>
  <div id="app" class="cmdb-app" ref="appRef"
    :class="{
      'no-breadcrumb': hideBreadcrumbs,
      'main-full-screen': mainFullScreen
    }">
    <CmdbHeader />
    <router-view class="views-layout"></router-view>
  </div>
</template>

<script>
import CmdbHeader from '@/components/layout/header.vue'
import { mapGetters } from 'vuex'

function throttle(fn, delay = 200) {
  let timer = null
  return function () {
    if (timer) return
    timer = setTimeout(() => {
      fn.apply(this, arguments)
      timer = null
    }, delay)
  }
}

export default {
  name: 'App',
  components: {
    CmdbHeader
  },
  data() {
    return {
      resizeHandler: null
    }
  },
  computed: {
    ...mapGetters(['mainFullScreen']),
    hideBreadcrumbs() {
      return !(this.$route.meta.layout || {}).breadcrumbs
    }
  },
  created() {
    this.resizeHandler = throttle(() => this.calculateAppHeight(), 200)
  },
  mounted() {
    this.calculateAppHeight()
    window.addEventListener('resize', this.resizeHandler)
  },
  beforeDestroy() {
    if (this.resizeHandler) {
      window.removeEventListener('resize', this.resizeHandler)
    }
  },
  methods: {
    calculateAppHeight() {
      const el = this.$refs.appRef || document.getElementById('app')
      const height = el ? (el.getBoundingClientRect?.().height || el.offsetHeight) : window.innerHeight
      this.$store.commit('setAppHeight', height)
    }
  }
}
</script>

<style lang="scss">
@import '@/assets/scss/common.scss';

#app {
  height: 100vh;
  overflow: hidden;
}

.cmdb-app {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.views-layout {
  height: calc(100% - 52px);
  overflow: hidden;
  background: #f5f7fa;
  position: relative;
}

.main-full-screen {
  .header-layout,
  .nav-layout,
  .breadcrumbs-layout {
    display: none;
  }

  .views-layout {
    height: 100%;
  }
}

.no-breadcrumb {
  .main-layout {
    height: 100%;
  }
}
</style>
