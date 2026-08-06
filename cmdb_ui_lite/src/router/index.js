import Vue from 'vue'
import VueRouter from 'vue-router'
import dynamicRouterView from '@/components/layout/dynamic-router-view'
import {
  MENU_BUSINESS,
  MENU_BUSINESS_TOPOLOGY,
  MENU_BUSINESS_HOST_DETAILS,
  MENU_RESOURCE,
  MENU_RESOURCE_MANAGEMENT,
  MENU_RESOURCE_INSTANCE,
  MENU_RESOURCE_INSTANCE_DETAILS,
  MENU_RESOURCE_HOST_DETAILS,
  MENU_MODEL,
  MENU_MODEL_MANAGEMENT
} from '@/dictionary/menu-symbol'
import store from '@/store'
import { getCachedBizId, setCachedBizId, DEFAULT_BIZ_ID } from '@/utils/biz-cache'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    // 对齐原项目：根路径重定向到「缓存/选中的业务」，而非固定 biz 2
    redirect: () => ({ path: `/business/${getCachedBizId()}/index` })
  },
  {
    name: MENU_BUSINESS,
    component: dynamicRouterView,
    path: '/business',
    // 对齐原项目：/business 顶层重定向到「缓存/选中的业务」，而非固定 biz 2
    // （函数式重定向，运行时读取 selectedBusiness；避免回业务时落回 biz2 并覆盖缓存）
    redirect: () => ({ path: `/business/${getCachedBizId()}/index` }),
    meta: {
      menu: {
        i18n: '业务'
      }
    },
    children: [
      {
        name: MENU_BUSINESS_TOPOLOGY,
        path: ':bizId/index',
        component: () => import('@/views/business-topology/index.vue'),
        meta: {
          menu: {
            i18n: '业务拓扑'
          },
          layout: {
            breadcrumbs: true
          }
        },
        // 复刻原项目 bk-cmdb/src/ui/src/views/business-topology/router.config.js：
        // 主机详情(host/:id) 是「业务拓扑(index)」的【嵌套子路由】，而非兄弟路由。
        // 这样进入主机详情时，父路由 business-topology/index.vue（含拓扑树）保持挂载，
        // 拓扑树的节点展开状态保留在 bk-big-tree 组件内存中，不会因整页重建而丢失；
        // 返回时仅关闭浮层，拓扑树原样保留，符合"进入/返回主机详情不刷新重建拓扑树"的诉求。
        children: [
          {
            name: MENU_BUSINESS_HOST_DETAILS,
            path: 'host/:id',
            component: () => import('@/views/host-details/index.vue'),
            meta: {
              menu: {
                i18n: '主机详情',
                relative: MENU_BUSINESS_TOPOLOGY
              },
              layout: {
                breadcrumbs: true
              }
            }
          }
        ]
      }
    ]
  },
  {
    name: MENU_RESOURCE,
    component: dynamicRouterView,
    path: '/resource',
    redirect: { name: MENU_RESOURCE_MANAGEMENT },
    meta: {
      menu: {
        i18n: '资源'
      }
    },
    children: [
      {
        name: MENU_RESOURCE_MANAGEMENT,
        path: 'index',
        component: () => import('@/views/resource/index.vue'),
        meta: {
          menu: {
            i18n: '资源目录'
          },
          layout: {
            breadcrumbs: true
          }
        }
      },
      {
        name: MENU_RESOURCE_INSTANCE,
        path: 'instance/:objId',
        component: () => import('@/views/general-model/index.vue'),
        meta: {
          menu: {
            i18n: '实例列表',
            relative: MENU_RESOURCE_MANAGEMENT
          },
          layout: {
            breadcrumbs: true
          }
        }
      },
      {
        name: MENU_RESOURCE_INSTANCE_DETAILS,
        path: 'instance/:objId/:instId',
        component: () => import('@/views/general-model/details.vue'),
        meta: {
          menu: {
            i18n: '实例详情'
          },
          layout: {
            breadcrumbs: true
          }
        }
      },
      {
        name: MENU_RESOURCE_HOST_DETAILS,
        path: 'host/:id',
        component: () => import('@/views/host-details/index.vue'),
        meta: {
          menu: {
            i18n: '主机详情',
            relative: MENU_RESOURCE_MANAGEMENT
          },
          layout: {
            breadcrumbs: true
          }
        }
      }
    ]
  },
  {
    name: MENU_MODEL,
    component: dynamicRouterView,
    path: '/model',
    redirect: { name: MENU_MODEL_MANAGEMENT },
    meta: {
      menu: {
        i18n: '模型'
      }
    },
    children: [
      {
        name: MENU_MODEL_MANAGEMENT,
        path: 'index',
        component: () => import('@/views/model/index.vue'),
        meta: {
          menu: {
            i18n: '模型管理'
          },
          layout: {
            breadcrumbs: true
          }
        }
      }
    ]
  }
]

const router = new VueRouter({
  mode: 'hash',
  routes
})

// 业务路由的 bizId 处理 —— 对齐原项目 bk-cmdb
// （src/ui/src/router/business-interceptor.js 的 before 守卫逻辑）：
//   1. 取值优先级：路由参数 bizId > localStorage['selectedBusiness']（缓存）
//   2. 每次进入有效业务即「保存选中业务 + 数据绑定（store.commit objectBiz/setBizId）」
//   3. 若 URL 中 bizId 为 0/缺失，纠正为缓存/选中的 id（replace 重定向）
//   4. 首次进入且无任何来源时，回退 DEFAULT_BIZ_ID（蓝鲸平台=2）并写入缓存 + store
const BUSINESS_ROUTES = [MENU_BUSINESS_TOPOLOGY, MENU_BUSINESS_HOST_DETAILS]

router.beforeEach((to, from, next) => {
  if (!BUSINESS_ROUTES.includes(to.name)) {
    return next()
  }

  const paramBizId = to.params && to.params.bizId
  const paramValid = paramBizId && paramBizId !== '0' && Number(paramBizId) > 0
  const cached = getCachedBizId() // 读 localStorage['selectedBusiness']，无则回退 DEFAULT_BIZ_ID
  const cachedValid = cached && cached !== '0' && Number(cached) > 0
  const id = paramValid ? String(paramBizId) : (cachedValid ? cached : null)

  // 无任何来源（极端情况：无缓存且默认失效）：回退默认业务
  if (!id) {
    const defaultId = String(DEFAULT_BIZ_ID)
    setCachedBizId(defaultId)                     // localStorage['selectedBusiness'] = defaultId
    store.commit('objectBiz/setBizId', defaultId) // 数据绑定
    return next({
      name: to.name,
      params: { ...to.params, bizId: defaultId },
      query: to.query,
      replace: true
    })
  }

  // 与原项目一致：进入业务即「保存选中业务 + 数据绑定」
  setCachedBizId(id)                              // localStorage['selectedBusiness'] = id
  store.commit('objectBiz/setBizId', id)          // store 数据绑定（菜单链接/选择器据此联动）

  // URL 中 bizId 为 0/缺失时，纠正为缓存/选中的 id
  if (!paramValid) {
    return next({
      name: to.name,
      params: { ...to.params, bizId: id },
      query: to.query,
      replace: true
    })
  }

  next()
})

export default router
