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
