import Vue from 'vue'
import VueRouter from 'vue-router'
import dynamicRouterView from '@/components/layout/dynamic-router-view'
import {
  MENU_INDEX,
  MENU_BUSINESS,
  MENU_BUSINESS_TOPOLOGY,
  MENU_BUSINESS_HOST_DETAILS,
  MENU_BUSINESS_SERVICE_CATEGORY,
  MENU_RESOURCE,
  MENU_RESOURCE_MANAGEMENT,
  MENU_RESOURCE_INSTANCE,
  MENU_RESOURCE_INSTANCE_DETAILS,
  MENU_RESOURCE_HOST,
  MENU_RESOURCE_HOST_DETAILS,
  MENU_MODEL,
  MENU_MODEL_MANAGEMENT
} from '@/dictionary/menu-symbol'
import { BUILTIN_MODELS } from '@/dictionary/model-constants'
import store from '@/store'
import { getCachedBizId, setCachedBizId, DEFAULT_BIZ_ID } from '@/utils/biz-cache'
import { ensureAuth } from '@/auth'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    // 根路由默认转到首页 index（登录无回跳参数时的兜底落点）。
    // 如需恢复"根路径直达缓存/选中业务"，改为下面注释行的 redirect 即可。
    redirect: { name: MENU_INDEX }
    // redirect: () => ({ path: `/business/${getCachedBizId(store.getters['user/userName'])}/index` })
  },
  {
    // 首页（占位骨架）：登录无回跳参数/参数异常时的兜底落点，
    // 同时在顶部导航栏与左侧导航栏固定为首位（见 dictionary/menu.js）
    name: MENU_INDEX,
    path: '/index',
    component: () => import('@/views/index/index.vue'),
    meta: {
      menu: {
        i18n: '首页'
      },
      layout: {
        breadcrumbs: false
      }
    }
  },
  {
    name: MENU_BUSINESS,
    component: dynamicRouterView,
    path: '/business',
    // 对齐原项目：/business 顶层重定向到「缓存/选中的业务」，而非固定 biz 2
    // （函数式重定向，运行时按用户作用域读取 selectedBusiness；避免回业务时落回 biz2 并覆盖缓存）
    redirect: () => ({ path: `/business/${getCachedBizId(store.getters['user/userName'])}/index` }),
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
      },
      {
        // 所属服务分类：对齐原项目 bk-cmdb 的独立路由
        // （原项目 owner=MENU_BUSINESS、path=service/cagetory，即 #/business/:bizId/service/cagetory）。
        // 与「业务拓扑」同为 /business/:bizId 下的兄弟路由，共享业务上下文（bizId）。
        name: MENU_BUSINESS_SERVICE_CATEGORY,
        path: ':bizId/service/cagetory',
        component: () => import('@/views/service-category/index.vue'),
        meta: {
          menu: {
            i18n: '服务分类'
          },
          layout: {
            breadcrumbs: true
          }
        }
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
        // 归一化 host 入口：host 是内置模型，统一使用专属路由 /resource/host
        // （与「主机」收藏项一致，确保实例列表/详情/收藏三入口选中态同步）。
        // 直接访问 #/resource/instance/host 等历史/外部 URL 时自动收敛到专属路由。
        beforeEnter: (to, from, next) => {
          if (to.params.objId === BUILTIN_MODELS.HOST) {
            return next({ name: MENU_RESOURCE_HOST })
          }
          next()
        },
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
            i18n: '实例详情',
            relative: MENU_RESOURCE_MANAGEMENT
          },
          layout: {
            breadcrumbs: true
          }
        }
      },
      {
        name: MENU_RESOURCE_HOST,
        path: 'host',
        component: () => import('@/views/general-model/index.vue'),
        meta: {
          menu: {
            i18n: '主机',
            // host 为内置模型，其列表/详情页共享 /resource/host 前缀；
            // 详情页路由名 MENU_RESOURCE_HOST_DETAILS 的 path 为 host/:id，
            // 该路由的 router-link 会在详情页被包含式命中，从而保持「主机」收藏项高亮。
            relative: MENU_RESOURCE_MANAGEMENT
          },
          layout: {
            breadcrumbs: true
          },
          // 路由级显式模型标识：本路由即「主机」资源列表，供 general-model 取得 objId，
          // 非通用实例路由的兜底默认值（通用实例路由缺 objId 仍按 resolveObjId 报错回首页）。
          objId: 'host'
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
  },
  {
    // 独立登录页（免登录模式下一般不会被自动跳转进入）
    path: '/login',
    name: 'login',
    component: () => import('@/views/login/index.vue'),
    meta: { public: true }
  }
]

const router = new VueRouter({
  mode: 'hash',
  routes
})

// 业务路由的 bizId 处理 —— 对齐原项目 bk-cmdb
// （src/ui/src/router/business-interceptor.js 的 before 守卫逻辑），并按用户作用域缓存：
//   1. 取值优先级：路由参数 bizId > 当前用户缓存 selectedBusiness_<userName>（localStorage）
//   2. 每次进入有效业务即「保存选中业务（写当前用户专属键）+ 数据绑定（store.commit objectBiz/setBizId）」
//   3. 若 URL 中 bizId 为 0/缺失，纠正为缓存/选中的 id（replace 重定向）
//   4. 首次进入且无任何来源时，回退 DEFAULT_BIZ_ID（蓝鲸平台=2）并写入当前用户缓存 + store
const BUSINESS_ROUTES = [MENU_BUSINESS_TOPOLOGY, MENU_BUSINESS_HOST_DETAILS, MENU_BUSINESS_SERVICE_CATEGORY]

router.beforeEach(async (to, from, next) => {
  // ── 最小内置鉴权守卫 ──
  // 非登录页：先确认登录态（skipLogin 直接放行；否则需有效 token）。
  // 未登录 → 跳登录页并携带 redirect 回跳地址。
  if (to.path !== '/login') {
    const authed = await ensureAuth()
    if (!authed) {
      return next({ path: '/login', query: { redirect: to.fullPath } })
    }
  }

  // 当前登录用户（用于业务 ID 的「用户范围」缓存，避免多用户互相覆盖）
  const userName = store.getters['user/userName'] || ''

  if (!BUSINESS_ROUTES.includes(to.name)) {
    return next()
  }

  const paramBizId = to.params && to.params.bizId
  const paramValid = paramBizId && paramBizId !== '0' && Number(paramBizId) > 0
  const cached = getCachedBizId(userName) // 读当前用户专属键 selectedBusiness_<userName>，无则回退 DEFAULT_BIZ_ID
  const cachedValid = cached && cached !== '0' && Number(cached) > 0
  const id = paramValid ? String(paramBizId) : (cachedValid ? cached : null)

  // 无任何来源（极端情况：无缓存且默认失效）：回退默认业务
  if (!id) {
    const defaultId = String(DEFAULT_BIZ_ID)
    setCachedBizId(defaultId, userName)          // selectedBusiness_<userName> = defaultId
    store.commit('objectBiz/setBizId', defaultId) // 数据绑定
    return next({
      name: to.name,
      params: { ...to.params, bizId: defaultId },
      query: to.query,
      replace: true
    })
  }

  // 与原项目一致：进入业务即「保存选中业务（写当前用户专属键）+ 数据绑定」
  setCachedBizId(id, userName)                    // selectedBusiness_<userName> = id
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
