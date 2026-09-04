import {
  MENU_INDEX,
  MENU_BUSINESS,
  MENU_BUSINESS_TOPOLOGY,
  MENU_BUSINESS_SERVICE_CATEGORY,
  MENU_RESOURCE,
  MENU_MODEL,
  MENU_RESOURCE_MANAGEMENT,
  MENU_MODEL_MANAGEMENT
} from './menu-symbol'
import { DEFAULT_BIZ_ID } from '@/utils/biz-cache'

const menus = [{
  // 首页：顶部导航栏与左侧导航栏固定首位（业务/资源/模型依次其后）
  id: MENU_INDEX,
  i18n: '首页',
  icon: 'icon-cc-home',
  route: {
    name: MENU_INDEX
  }
}, {
  id: MENU_BUSINESS,
  i18n: '业务',
  menu: [{
    id: MENU_BUSINESS_TOPOLOGY,
    i18n: '业务拓扑',
    icon: 'icon-cc-host',
    route: {
      name: MENU_BUSINESS_TOPOLOGY,
      params: {
        bizId: DEFAULT_BIZ_ID
      }
    }
  }, {
    // 所属服务分类：对齐原项目 bk-cmdb 的「业务 → 服务分类」独立入口
    // （原项目路由 owner=MENU_BUSINESS、path=service/cagetory，即 /business/:bizId/service/cagetory）。
    // 在 lite 中作为「业务」左侧导航的同级菜单项，与业务拓扑并列。
    id: MENU_BUSINESS_SERVICE_CATEGORY,
    i18n: '服务分类',
    icon: 'icon-cc-nav-service-topo',
    route: {
      name: MENU_BUSINESS_SERVICE_CATEGORY,
      params: {
        bizId: DEFAULT_BIZ_ID
      }
    }
  }]
  },   {
    id: MENU_RESOURCE,
    i18n: '资源',
    menu: [{
      id: MENU_RESOURCE_MANAGEMENT,
      i18n: '资源目录',
      icon: 'icon-cc-square',
      // 精确指向 /resource/index（与原项目一致）。
      // 在实例页 #/resource/instance/:objId（含详情页 */*）下的"选中态"由 dynamic-navigation.vue
      // 的 relative-active 机制根据路由 meta.menu.relative 派生：
      // - 该 objId 为自定义收藏 → 收藏菜单项精确命中，资源目录不亮（优先突出收藏）；
      // - 该 objId 非收藏 → 资源目录通过 is-relative-active 保持选中，与 #/resource/index 一致。
      route: {
        name: MENU_RESOURCE_MANAGEMENT
      }
    }]
  }]

// 暂时未开发：模型（MENU_MODEL）入口暂不展示于头部导航菜单栏
// , {
//   id: MENU_MODEL,
//   i18n: '模型',
//   menu: [{
//     id: MENU_MODEL_MANAGEMENT,
//     i18n: '模型管理',
//     icon: 'icon-cc-nav-model-02',
//     route: {
//       name: MENU_MODEL_MANAGEMENT
//     }
//   }]
// }

export default menus
