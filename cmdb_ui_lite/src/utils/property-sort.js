/**
 * 属性列排序规则（复刻原项目 src/ui/src/utils/tools.js）
 *
 * 原项目实现参考：
 *   - isPropertySortable(property)
 *   - getSort(sort, defaultSort)
 * 属性类型取值参考：
 *   - src/ui/src/dictionary/property-constants.js 的 PROPERTY_TYPES
 * 模型标识参考：
 *   - src/ui/src/dictionary/model-constants.js 的 BUILTIN_MODELS.HOST = 'host'
 */

// 属性类型常量（对齐原项目 PROPERTY_TYPES）
export const PROPERTY_TYPES = Object.freeze({
  SINGLECHAR: 'singlechar',
  INT: 'int',
  FLOAT: 'float',
  ENUM: 'enum',
  DATE: 'date',
  TIME: 'time',
  LONGCHAR: 'longchar',
  OBJUSER: 'objuser',
  TIMEZONE: 'timezone',
  BOOL: 'bool',
  LIST: 'list',
  ORGANIZATION: 'organization',
  ENUMMULTI: 'enummulti',
  ENUMQUOTE: 'enumquote',
  MAP: 'map',
  OBJECT: 'object',
  ARRAY: 'array',
  TABLE: 'table',
  SERVICE_TEMPLATE: 'service-template',
  TOPOLOGY: 'topology',
  FOREIGNKEY: 'foreignkey',
  INNER_TABLE: 'innertable'
})

// 内置模型：主机（对齐原项目 BUILTIN_MODELS.HOST）
export const BUILTIN_MODEL_HOST = 'host'

/**
 * 判断属性列是否支持排序（按属性类型规则）
 *
 * 复刻原项目 isPropertySortable：
 *   - 主机(host)属性：排除 foreignkey / topology / inner_table 三类不可排序
 *   - 非主机属性（如 set / module 关联属性）：不支持排序（与原项目一致，模块和集群列不可排序）
 * 其余标量、枚举、时间等类型均可排序。
 *
 * @param {Object} property 属性定义，需包含 bk_obj_id 与 bk_property_type
 * @returns {Boolean} 是否可排序
 */
export function isPropertySortable(property = {}) {
  if (property.bk_obj_id === BUILTIN_MODEL_HOST) {
    return ![PROPERTY_TYPES.FOREIGNKEY, PROPERTY_TYPES.TOPOLOGY, PROPERTY_TYPES.INNER_TABLE]
      .includes(property.bk_property_type)
  }
  return false
}

/**
 * 将 bk-table 的 sort-change 事件参数转换为后端排序字段
 *
 * 复刻原项目 getSort：当排序方向为 descending 时，字段前加 '-' 前缀；
 * 其余（ascending / 默认）仅返回字段名。最终值直接作为 HostCommonSearch
 * 请求体 page.sort 下发（如 'bk_host_id' 或 '-bk_host_name'）。
 *
 * @param {Object} sort bk-table sort-change 事件参数 { prop, order }
 * @param {Object} [defaultSort] 兜底排序 { prop, order }
 * @returns {String} 后端排序字段
 */
export function getSort(sort, defaultSort = {}) {
  const order = sort.order || defaultSort.order || 'ascending'
  const prop = sort.prop || defaultSort.prop || ''
  if (prop && order === 'descending') {
    return `-${prop}`
  }
  return prop
}

// 属性分组显示名映射（对齐原项目 bk-cmdb 内置分组命名）
export const GROUP_NAME_MAP = Object.freeze({
  'default': '基础信息',
  'auto': '自动发现信息（需要安装agent）',
  'role': '角色',
  'proc_port': '监听信息'
})

/**
 * 按 bk_group_index 对属性分组排序，与详情页 effectivePropertyGroups 保持一致。
 *
 * 复刻 src/views/host-details/index.vue 的 effectivePropertyGroups 算法：
 *   1) 属性分组接口(propertyGroups)返回的 bk_group_index 为权威排序来源；
 *   2) 属性中出现的「未登记分组」(接口未返回)，按其在属性列表中的首次出现顺序
 *      分配连续索引（复刻 dynamicPropertyGroups），从而在未登记分组之间、以及
 *      与已登记分组之间保持与详情页一致的先后关系；
 *   3) 每个分组内的属性按 bk_property_index 升序。
 *
 * @param {Array} properties 当前表单属性列表（每个含 bk_property_group / bk_property_index）
 * @param {Array} [propertyGroups] 属性分组接口数据（含 bk_group_id / bk_group_index / bk_group_name）
 * @param {Object} [groupNameMap] 分组显示名兜底映射（缺省用 GROUP_NAME_MAP）
 * @returns {Array} 已排序的分组数组 [{ bk_group_id, bk_group_name, bk_group_index, properties }]
 */
export function sortPropertyGroups(properties = [], propertyGroups = [], groupNameMap = GROUP_NAME_MAP) {
  // 1) API 分组元数据（bk_group_index 为权威排序来源）
  const apiMeta = {}
  ;(propertyGroups || []).forEach((g) => {
    if (g && g.bk_group_id) {
      const index = (g.bk_group_index === undefined || g.bk_group_index === null)
        ? 99
        : g.bk_group_index
      apiMeta[g.bk_group_id] = {
        index,
        name: g.bk_group_name || groupNameMap[g.bk_group_id] || g.bk_group_id
      }
    }
  })

  // 2) 属性首次出现顺序 -> 未登记分组的兜底索引（复刻详情页 dynamicPropertyGroups）
  const dynamicIndex = {}
  let orderIndex = 0
  properties.forEach((property) => {
    const groupId = property.bk_property_group === 'none'
      ? 'default'
      : (property.bk_property_group || 'default')
    if (!(groupId in dynamicIndex)) {
      dynamicIndex[groupId] = orderIndex
      orderIndex += 1
    }
  })

  // 3) 归集分组：已登记分组用 API 索引，未登记分组用首次出现索引
  const groups = {}
  properties.forEach((property) => {
    const groupId = property.bk_property_group === 'none'
      ? 'default'
      : (property.bk_property_group || 'default')
    if (!groups[groupId]) {
      const m = apiMeta[groupId]
      const index = m ? m.index : (dynamicIndex[groupId] ?? 99)
      groups[groupId] = {
        bk_group_id: groupId,
        bk_group_name: m ? m.name : (groupNameMap[groupId] || groupId),
        bk_group_index: index,
        properties: []
      }
    }
    groups[groupId].properties.push(property)
  })

  // 组内属性按 bk_property_index 升序
  Object.values(groups).forEach((group) => {
    group.properties.sort((a, b) => (a.bk_property_index || 0) - (b.bk_property_index || 0))
  })

  // 分组按 bk_group_index 排序（与详情页 effectivePropertyGroups 一致）
  return Object.values(groups)
    .sort((a, b) => (a.bk_group_index ?? 99) - (b.bk_group_index ?? 99))
}
