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

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    redirect: '/business/2/index'
  },
  {
    name: MENU_BUSINESS,
    component: dynamicRouterView,
    path: '/business',
    redirect: '/business/2/index',
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
        }
      },
      {
        name: MENU_BUSINESS_HOST_DETAILS,
        path: ':bizId/index/host/:id',
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

export default router
