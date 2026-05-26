import Vue from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'

import bkMagic from 'bk-magic-vue'
import 'bk-magic-vue/dist/bk-magic-vue.min.css'
import '@/assets/icon/bk-icon-cmdb/style.css'
import '@/assets/scss/common.scss'

import { initRouterQuery } from '@/utils/router-query'
import SearchComponents from '@/components/search'
import CmdbFormComponents from '@/components/ui/form'
import userCustom from '@/api/user-custom'

Vue.use(bkMagic)
Vue.use(SearchComponents)
Vue.use(CmdbFormComponents)

Vue.config.productionTip = false

const app = new Vue({
  router,
  store,
  async created() {
    console.log('[App] 应用启动中...')
    
    // 加载用户配置到 Vuex Store
    try {
      console.log('[App] 正在加载用户配置...')
      const allCustom = await userCustom.searchUserCustom()
      
      // 确保 allCustom 是对象
      if (allCustom && typeof allCustom === 'object') {
        this.$store.dispatch('loadAllUserCustom', allCustom)
        console.log('[App] ✅ 用户配置已加载到 Vuex Store')
        console.log('[App] 加载的配置项:', Object.keys(allCustom))
        
        // 打印自定义列配置
        Object.keys(allCustom).forEach(key => {
          if (key.includes('custom_table_columns')) {
            console.log(`[App]   ${key}:`, allCustom[key])
          }
        })
      } else {
        console.warn('[App] ⚠️ 用户配置为空或格式错误:', allCustom)
      }
    } catch (e) {
      console.error('[App] ❌ 加载用户配置失败:', e)
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
