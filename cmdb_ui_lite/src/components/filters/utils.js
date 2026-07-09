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
  if (type === 'int' || type === 'float' || type === 'double' || type === 'long') {
    if (operator === 'RANGE') {
      return (value && Array.isArray(value)) ? value : ['', '']
    }
    if (operator === 'IN' || operator === 'NIN') {
      return (value && Array.isArray(value)) ? value : []
    }
  }

  if (type === 'enummulti' || type === 'list') {
    if (operator === 'IN' || operator === 'NIN') {
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

export default {
  DEFAULT_IP,
  getDefaultIP,
  getPlaceholder,
  getOperatorSideEffect,
  numberUseIn
}