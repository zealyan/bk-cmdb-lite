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
import ResizeLayout from '@/components/ui/other/resize.vue'
import CmdDialog from '@/components/ui/dialog/dialog.vue'
import userCustom from '@/api/user-custom'
import cmdbAppMixin from './mixins/app.js'
import { bindMagic, handleApiError } from '@/utils/error-handler'

Vue.use(bkMagic)
Vue.use(SearchComponents)
Vue.use(CmdbFormComponents)
Vue.component('cmdb-resize-layout', ResizeLayout)
Vue.component('cmdb-dialog', CmdDialog)
// 统一错误呈现：组件 catch 中调用 this.$handleApiError(error) 即可
Vue.prototype.$handleApiError = handleApiError
// 移植自原项目：v-transfer-dom，把弹框挂到 body，
// 避免祖先元素的 transform 破坏 .dialog-wrapper 的 position: fixed 视口定位。
Vue.directive('transfer-dom', {
  inserted(el, binding) {
    const target = binding.value ? document.querySelector(binding.value) : document.body
    if (target) target.appendChild(el)
  },
  unbind(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el)
  }
})
Vue.mixin(cmdbAppMixin)

Vue.config.productionTip = false

const app = new Vue({
  router,
  store,
  async created() {
    // 注入 bkMagic 实例，供统一错误处理器（error-handler.js）弹出无权限对话框
    bindMagic(this)
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
