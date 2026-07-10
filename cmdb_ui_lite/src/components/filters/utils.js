const DEFAULT_IP = {
  text: '',
  inner: true,
  outer: true,
  exact: false
}

const getDefaultIP = () => {
  return { ...DEFAULT_IP }
}

const getPlaceholder = (property) => {
  const { bk_property_name, bk_property_type } = property
  const typeMap = {
    singlechar: `请输入${bk_property_name}`,
    shortchar: `请输入${bk_property_name}`,
    longchar: `请输入${bk_property_name}`,
    text: `请输入${bk_property_name}`,
    textarea: `请输入${bk_property_name}`,
    int: `请输入${bk_property_name}`,
    float: `请输入${bk_property_name}`,
    double: `请输入${bk_property_name}`,
    long: `请输入${bk_property_name}`,
    enum: `请选择${bk_property_name}`,
    enummulti: `请选择${bk_property_name}`,
    list: `请选择${bk_property_name}`,
    bool: `请选择${bk_property_name}`,
    date: `请选择${bk_property_name}`,
    time: `请选择${bk_property_name}`,
    datetime: `请选择${bk_property_name}`
  }
  return typeMap[bk_property_type] || `请输入${bk_property_name}`
}

const getOperatorSideEffect = (property, operator, value) => {
  if (!property) return value
  if (!operator) return value

  const type = property.bk_property_type
  const isArrayOp = ['$in', '$nin'].includes(operator)

  // 数组类型操作符（$in/$nin）：value 必须是数组
  if (isArrayOp) {
    if (Array.isArray(value)) return value
    if (typeof value === 'string' && value.length > 0) return [value]
    return []
  }

  // 范围操作符（$range）：value 必须是数组
  if (operator === '$range') {
    if (Array.isArray(value) && value.length >= 2) return value
    return ['', '']
  }

  // 数值类型的 $in/$nin 也返回数组
  if (type === 'int' || type === 'float' || type === 'double' || type === 'long') {
    if (operator === '$in' || operator === '$nin') {
      return (value && Array.isArray(value)) ? value : []
    }
  }

  if (type === 'enummulti' || type === 'list') {
    if (operator === '$in' || operator === '$nin') {
      return (value && Array.isArray(value)) ? value : []
    }
  }

  return value
}

const numberUseIn = (property, operator) => {
  if (!property || !operator) return false
  const type = property.bk_property_type
  return ['int', 'float', 'double', 'long'].includes(type) && ['IN', 'NIN'].includes(operator)
}

const getDefaultData = (property, defaultData = { operator: '$in', value: [] }) => {
  const defaultMap = {
    singlechar: { operator: '$in', value: [] },
    shortchar: { operator: '$in', value: [] },
    int: { operator: '$eq', value: '' },
    long: { operator: '$eq', value: '' },
    float: { operator: '$eq', value: '' },
    double: { operator: '$eq', value: '' },
    enum: { operator: '$in', value: [] },
    enummulti: { operator: '$in', value: [] },
    date: { operator: '$range', value: [] },
    time: { operator: '$range', value: [] },
    datetime: { operator: '$eq', value: '' },
    longchar: { operator: '$in', value: [] },
    text: { operator: '$in', value: [] },
    char: { operator: '$in', value: [] },
    objuser: { operator: '$in', value: [] },
    timezone: { operator: '$in', value: [] },
    bool: { operator: '$eq', value: '' },
    list: { operator: '$in', value: [] },
    organization: { operator: '$in', value: [] },
    array: { operator: '$in', value: [] },
    map: { operator: '$in', value: [] },
    object: { operator: '$in', value: [] },
    foreignkey: { operator: '$in', value: [] },
    table: { operator: '$in', value: [] }
  }

  return {
    operator: defaultData.operator,
    value: defaultData.value,
    ...(defaultMap[property?.bk_property_type] || { operator: '$eq', value: '' })
  }
}

const QUERY_OPERATOR_SYMBOL = {
  '$eq': '=',
  '$ne': '≠',
  '$in': 'in',
  '$nin': 'not in',
  '$gt': '>',
  '$lt': '<',
  '$gte': '≥',
  '$lte': '≤',
  '$regex': 'like',
  '$range': '≤ ≥',
  '$contains': 'contains',
  '$contains_s': 'contains(CS)'
}

const getOperatorSymbol = (operator, symbolMap) => {
  const data = symbolMap || QUERY_OPERATOR_SYMBOL
  return data[operator]
}

const splitIP = (raw) => {
  const list = []
  if (!raw) return list
  raw.trim().split(/\n|;|；|,|，/)
    .forEach((text) => {
      const ip = text.trim()
      ip.length && list.push(ip)
    })
  return list
}

export default {
  DEFAULT_IP,
  getDefaultIP,
  getPlaceholder,
  getOperatorSideEffect,
  numberUseIn,
  getOperatorSymbol,
  getDefaultData,
  splitIP
}