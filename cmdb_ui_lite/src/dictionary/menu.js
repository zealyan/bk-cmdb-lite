import {
  MENU_BUSINESS,
  MENU_BUSINESS_TOPOLOGY,
  MENU_RESOURCE,
  MENU_MODEL,
  MENU_RESOURCE_MANAGEMENT,
  MENU_MODEL_MANAGEMENT
} from './menu-symbol'
import { DEFAULT_BIZ_ID } from '@/utils/biz-cache'

const menus = [{
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
  }]
}, {
  id: MENU_RESOURCE,
  i18n: '资源',
  menu: [{
    id: MENU_RESOURCE_MANAGEMENT,
    i18n: '资源目录',
    icon: 'icon-cc-square',
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
