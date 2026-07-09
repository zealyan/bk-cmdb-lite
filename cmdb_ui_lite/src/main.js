import Vue from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'

import bkMagic from 'bk-magic-vue'
import 'bk-magic-vue/dist/bk-magic-vue.min.css'
import '@/assets/icon/bk-icon-cmdb/style.css'
import '@/assets/scss/common.scss'
import '@/assets/scss/magicbox.scss'

import { initRouterQuery } from '@/utils/router-query'
import SearchComponents from '@/components/search'
import CmdbFormComponents from '@/components/ui/form'
import userCustom from '@/api/user-custom'
import cmdbAppMixin from './mixins/app.js'

Vue.use(bkMagic)
Vue.use(SearchComponents)
Vue.use(CmdbFormComponents)
Vue.mixin(cmdbAppMixin)

Vue.config.productionTip = false

const app = new Vue({
  router,
  store,
  async created() {
    console.log('[App] 应用启动中...')
    
    // 并行加载模型分类数据和用户配置
    try {
      console.log('[App] 正在加载模型分类和用户配置...')
      
      const [classificationsData, userCustomData] = await Promise.allSettled([
        this.$store.dispatch('objectModelClassify/searchClassificationsObjects'),
        this.$store.dispatch('userCustom/searchUsercustom')
      ])
      
      if (classificationsData.status === 'fulfilled') {
        console.log('[App] ✅ 模型分类数据已加载')
      } else {
        console.error('[App] ❌ 模型分类数据加载失败:', classificationsData.reason)
      }
      
      if (userCustomData.status === 'fulfilled') {
        console.log('[App] ✅ 用户配置已加载')
        console.log('[App] 加载的配置项:', Object.keys(userCustomData.value || {}))
      } else {
        console.error('[App] ❌ 用户配置加载失败:', userCustomData.reason)
      }

      // 兼容旧方式：加载到全局 state
      if (userCustomData.status === 'fulfilled' && userCustomData.value) {
        this.$store.dispatch('loadAllUserCustom', userCustomData.value)
      }
      
    } catch (e) {
      console.error('[App] ❌ 初始化加载失败:', e)
    }
    
    console.log('[App] 应用启动完成')
  },
  render: h => h(App)
})

initRouterQuery(router, app)

app.$mount('#app')

import VConsole from 'vconsole'
const vConsole = new VConsole({ theme: 'dark' })
console.log('[vConsole] 移动端调试面板已启动')
