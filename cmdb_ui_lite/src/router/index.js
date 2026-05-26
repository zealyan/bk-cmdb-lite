import Vue from 'vue'
import VueRouter from 'vue-router'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    redirect: '/resource/index'
  },
  {
    path: '/resource/index',
    name: 'ResourceIndex',
    component: () => import('@/views/resource/index.vue')
  },
  {
    path: '/resource/host',
    name: 'ResourceHost',
    component: () => import('@/views/resource/host.vue')
  },
  {
    path: '/resource/host/:id',
    name: 'ResourceHostDetails',
    component: () => import('@/views/resource/host-details.vue')
  },
  {
    path: '/resource/instance/:objId',
    name: 'ResourceInstanceList',
    component: () => import('@/views/general-model/index.vue')
  },
  {
    path: '/resource/instance/:objId/:instId',
    name: 'ResourceInstanceDetails',
    component: () => import('@/views/general-model/details.vue')
  }
]

const router = new VueRouter({
  mode: 'hash',
  routes
})

export default router
