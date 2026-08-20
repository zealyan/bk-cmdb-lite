/**
 * 属性值显示辅助：把枚举 / 多选枚举 / 列表 类型存储的「键」映射为「显示名」。
 *
 * 与 components/property/CmdbPropertyValue.vue 的 buildOptionMap 逻辑保持一致，
 * 供主机列表（general-model/index.vue、business-topology/host/host-list.vue）等
 * 直接渲染单元格值的场景复用，避免多处实现漂移。
 *
 * option 支持三种来源格式（与后端 / 上游 bk-cmdb 兼容）：
 *   1) 数组 [{id, name, ...}]       → { [id]: name }
 *   2) 字符串数组 ["a","b"]         → { [v]: v }（键即显示名）
 *   3) 旧式对象 { "key": "name" }    → 原样
 */

export function buildOptionMap(option) {
  if (!option) return null
  let parsed = option
  if (typeof option === 'string') {
    try {
      parsed = JSON.parse(option)
    } catch (e) {
      return null
    }
  }
  if (Array.isArray(parsed)) {
    const map = {}
    parsed.forEach((opt) => {
      if (opt && opt.id !== undefined) {
        map[String(opt.id)] = opt.name
      } else if (typeof opt === 'string') {
        map[opt] = opt
      }
    })
    return map
  }
  if (parsed && typeof parsed === 'object') {
    return parsed
  }
  return null
}

function isEmpty(val) {
  return val === null || val === undefined || val === ''
}

/**
 * 根据属性定义把单元格原始值格式化为可展示文本。
 * @param {*} value        单元格原始值（枚举存的是 key，多选枚举可能是数组）
 * @param {Object} property 属性定义（需含 bk_property_type 与 option）
 * @returns {string} 展示文本（空值返回 '-'）
 */
export function formatPropertyValue(value, property) {
  if (isEmpty(value)) {
    return '-'
  }

  const propertyType = (property && property.bk_property_type) || ''

  if (propertyType === 'enum' || propertyType === 'enummulti' || propertyType === 'list') {
    const map = buildOptionMap(property && property.option)
    if (map) {
      if (Array.isArray(value)) {
        const names = value
          .map(v => map[String(v)])
          .filter(n => n !== undefined && n !== null && n !== '')
        return names.length ? names.join(', ') : String(value)
      }
      const name = map[String(value)]
      if (name !== undefined && name !== null && name !== '') {
        return name
      }
    }
  }

  if (propertyType === 'bool') {
    const lower = String(value).toLowerCase()
    if (lower === 'true' || lower === '1') return '是'
    if (lower === 'false' || lower === '0') return '否'
  }

  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}
