<template>
  <div id="app" class="cmdb-app">
    <CmdbHeader />
    <div class="views-layout">
      <div class="page-breadcrumbs" v-if="showBreadcrumbs">
        <i class="icon icon-cc-arrow fl" @click="handleBack"></i>
        <div class="breadcrumbs-content">
          <template v-if="isListPage">
            <span class="breadcrumb-current">{{ breadcrumbs[0] }}</span>
          </template>
          <template v-else>
            <span class="breadcrumb-item" @click="goToInstanceList">{{ breadcrumbs[0] }}</span>
            <span class="breadcrumb-separator">/</span>
            <span class="breadcrumb-current">{{ breadcrumbs[1] }}</span>
          </template>
        </div>
      </div>
      <router-view />
    </div>
  </div>
</template>

<script>
import CmdbHeader from '@/components/layout/header.vue'
const STORAGE_KEY = 'cmdb_list_state'

export default {
  name: 'App',
  components: {
    CmdbHeader
  },
  data () {
    return {
      breadcrumbs: [],
      isListPage: true
    }
  },
  computed: {
    showBreadcrumbs () {
      return this.$route.name === 'ResourceInstanceList' || this.$route.name === 'ResourceInstanceDetails'
    }
  },
  watch: {
    $route (to, from) {
      this.updateBreadcrumbs(to)
      this.saveListState(to, from)
    },
    '$store.state.currentInstance': {
      handler (newVal) {
        if (newVal && newVal.name) {
          console.log('[App.watch] 实例名称更新:', newVal.name)
          this.updateBreadcrumbs(this.$route)
        }
      },
      deep: true
    }
  },
  mounted () {
    this.updateBreadcrumbs(this.$route)
  },
  methods: {
    saveListState (to, from) {
      console.log('[App.saveListState] 保存列表状态', { from: from.name, to: to.name })
      if (from.name === 'ResourceInstanceList') {
        const query = from.query
        console.log('[App.saveListState] 列表页query:', JSON.stringify(query))
        if (query && Object.keys(query).length > 0) {
          const state = { objId: from.params.objId, query: query }
          console.log('[App.saveListState] 保存状态到sessionStorage:', JSON.stringify(state))
          sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state))
        } else {
          console.log('[App.saveListState] query为空，不保存')
        }
      } else {
        console.log('[App.saveListState] 不是从列表页离开，不保存')
      }
    },
    updateBreadcrumbs (route) {
      console.log('[App.updateBreadcrumbs] 当前路由:', route.name, 'params:', route.params)
      
      if (route.name === 'ResourceInstanceList') {
        this.isListPage = true
        const objId = route.params.objId
        console.log('[App.updateBreadcrumbs] 列表页, objId:', objId)
        const modelNames = {
          bk_switch: '交换机',
          bk_host: '主机',
          bk_slb: '负载均衡',
          bk_slb_server: 'SLB服务器',
          bk_slb_listener: 'SLB监听器'
        }
        const modelName = modelNames[objId] || objId
        this.breadcrumbs = [modelName]
        console.log('[App.updateBreadcrumbs] 设置面包屑:', this.breadcrumbs)
      } else if (route.name === 'ResourceInstanceDetails') {
        this.isListPage = false
        const objId = route.params.objId
        const instId = route.params.instId
        const modelNames = {
          bk_switch: '交换机',
          bk_host: '主机',
          bk_slb: '负载均衡',
          bk_slb_server: 'SLB服务器',
          bk_slb_listener: 'SLB监听器'
        }
        // 从 store 获取实例名称
        const instanceName = this.$store.state.currentInstance?.name || `ID: ${instId}`
        this.breadcrumbs = [modelNames[objId] || objId, instanceName]
        console.log('[App.updateBreadcrumbs] 详情页, 设置面包屑:', this.breadcrumbs)
      }
    },
    handleBack () {
      this.$router.go(-1)
    },
    goToResource () {
      this.$router.push({ name: 'ResourceIndex' })
    },
    goToInstanceList () {
      const objId = this.$route.params.objId
      const currentQuery = this.$route.query
      console.log('[App.goToInstanceList] 当前详情页query:', JSON.stringify(currentQuery))
      console.log('[App.goToInstanceList] 当前objId:', objId)

      if (Object.keys(currentQuery).length > 0) {
        console.log('[App.goToInstanceList] 详情页有query，使用详情页query返回')
        this.$router.push({ name: 'ResourceInstanceList', params: { objId }, query: currentQuery })
      } else {
        console.log('[App.goToInstanceList] 详情页无query，检查sessionStorage')
        const savedState = sessionStorage.getItem(STORAGE_KEY)
        if (savedState) {
          try {
            const state = JSON.parse(savedState)
            console.log('[App.goToInstanceList] sessionStorage中的状态:', JSON.stringify(state))
            if (state.objId === objId && state.query && Object.keys(state.query).length > 0) {
              console.log('[App.goToInstanceList] 使用sessionStorage中的状态返回')
              this.$router.push({ name: 'ResourceInstanceList', params: { objId }, query: state.query })
              return
            } else {
              console.log('[App.goToInstanceList] sessionStorage状态不匹配或query为空')
            }
          } catch (e) {
            console.error('[App] 解析保存状态失败:', e)
          }
        } else {
          console.log('[App.goToInstanceList] sessionStorage中无保存状态')
        }
        console.log('[App.goToInstanceList] 直接返回列表页')
        this.$router.push({ name: 'ResourceInstanceList', params: { objId } })
      }
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
}

.views-layout {
  flex: 1;
  overflow-y: auto;
  background: #f5f7fa;
  position: relative;
}

.page-breadcrumbs {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 40px;
  background: #fff;
  border-bottom: 1px solid #eaeaea;

  .icon {
    font-size: 12px;
    color: #63656e;
    cursor: pointer;
    margin-right: 8px;

    &:hover {
      color: #3a84ff;
    }
  }

  .fl {
    float: left;
  }
}

.breadcrumbs-content {
  display: flex;
  align-items: center;
  font-size: 14px;

  .breadcrumb-item {
    color: #3a84ff;
    cursor: pointer;

    &:hover {
      text-decoration: underline;
    }
  }

  .breadcrumb-separator {
    margin: 0 8px;
    color: #c4c6cc;
  }

  .breadcrumb-current {
    color: #63656e;
  }
}
</style>
