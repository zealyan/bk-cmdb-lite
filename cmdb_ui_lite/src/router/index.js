import Vue from 'vue'
import VueRouter from 'vue-router'
import dynamicRouterView from '@/components/layout/dynamic-router-view'
import {
  MENU_RESOURCE,
  MENU_RESOURCE_MANAGEMENT,
  MENU_RESOURCE_HOST,
  MENU_RESOURCE_INSTANCE,
  MENU_RESOURCE_INSTANCE_DETAILS
} from '@/dictionary/menu-symbol'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    redirect: { name: MENU_RESOURCE_MANAGEMENT }
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
        name: MENU_RESOURCE_HOST,
        path: 'host',
        component: () => import('@/views/resource/host.vue'),
        meta: {
          menu: {
            i18n: '主机',
            relative: MENU_RESOURCE_MANAGEMENT
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
      }
    ]
  }
]

const router = new VueRouter({
  mode: 'hash',
  routes
})

export default router
