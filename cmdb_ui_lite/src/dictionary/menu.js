import {
  MENU_BUSINESS,
  MENU_BUSINESS_TOPOLOGY,
  MENU_RESOURCE,
  MENU_MODEL,
  MENU_RESOURCE_MANAGEMENT,
  MENU_MODEL_MANAGEMENT
} from './menu-symbol'

const menus = [{
  id: MENU_BUSINESS,
  i18n: '业务',
  menu: [{
    id: MENU_BUSINESS_TOPOLOGY,
    i18n: '业务拓扑',
    icon: 'icon-cc-topology',
    route: {
      name: MENU_BUSINESS_TOPOLOGY,
      params: {
        bizId: 2
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
}, {
  id: MENU_MODEL,
  i18n: '模型',
  menu: [{
    id: MENU_MODEL_MANAGEMENT,
    i18n: '模型管理',
    icon: 'icon-cc-nav-model-02',
    route: {
      name: MENU_MODEL_MANAGEMENT
    }
  }]
}]

export default menus
