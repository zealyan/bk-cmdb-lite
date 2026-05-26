import { QUERY_OPERATOR } from '@/utils/query-operator'

const escapeCharRE = /([\*\.\?\+\$\^\[\]\(\)\{\}\|\\\/])/g
const needEscapeOperator = [QUERY_OPERATOR.CONTAINS, QUERY_OPERATOR.LIKE, QUERY_OPERATOR.CONTAINS_CS]

export function getDefaultData(property) {
  if (!property) return { operator: QUERY_OPERATOR.EQ, value: '' }

  const type = property.bk_property_type
  const defaultMap = {
    int: { operator: QUERY_OPERATOR.EQ, value: null },
    float: { operator: QUERY_OPERATOR.EQ, value: null },
    bool: { operator: QUERY_OPERATOR.EQ, value: null },
    enum: { operator: QUERY_OPERATOR.IN, value: [] },
    list: { operator: QUERY_OPERATOR.IN, value: [] },
    map: { operator: QUERY_OPERATOR.EQ, value: {} },
    singlechar: { operator: QUERY_OPERATOR.IN, value: [] },
    longchar: { operator: QUERY_OPERATOR.IN, value: [] },
    objuser: { operator: QUERY_OPERATOR.IN, value: [] },
    timezone: { operator: QUERY_OPERATOR.IN, value: [] },
    organization: { operator: QUERY_OPERATOR.IN, value: [] },
    array: { operator: QUERY_OPERATOR.IN, value: [] }
  }

  return {
    operator: defaultMap[type]?.operator || QUERY_OPERATOR.IN,
    value: defaultMap[type]?.value ?? ''
  }
}

export function getOperatorSideEffect(property, operator, value) {
  let effectValue = value
  if (operator === QUERY_OPERATOR.RANGE) {
    effectValue = []
  } else if ([QUERY_OPERATOR.LIKE, QUERY_OPERATOR.CONTAINS, QUERY_OPERATOR.CONTAINS_CS].includes(operator)) {
    effectValue = Array.isArray(value) ? (value[0] || '') : value
  } else if (operator === QUERY_OPERATOR.IN || operator === QUERY_OPERATOR.NIN) {
    effectValue = Array.isArray(value) ? value : []
  } else {
    const defaultValue = getDefaultData(property).value
    const isTypeChanged = (Array.isArray(defaultValue)) !== (Array.isArray(value))
    effectValue = isTypeChanged ? defaultValue : value
  }
  return effectValue
}

export function convertValue(value, operator, property) {
  if (!property) return value

  const type = property.bk_property_type
  let convertedValue = Array.isArray(value) ? value : [value]
  convertedValue = convertedValue.map((data) => {
    if (['int', 'foreignkey'].includes(type)) {
      return parseInt(data, 10)
    }
    if (type === 'float') {
      return parseFloat(data, 10)
    }
    if (type === 'bool') {
      return data === 'true'
    }
    return data
  })
  if ([QUERY_OPERATOR.IN, QUERY_OPERATOR.NIN, QUERY_OPERATOR.RANGE].includes(operator)) {
    return convertedValue
  }
  return convertedValue[0]
}

export function getPlaceholder(property) {
  if (!property) return ''
  const name = property.bk_property_name || ''
  const type = property.bk_property_type

  const selectTypes = ['list', 'enum', 'timezone', 'organization', 'date', 'time']
  if (selectTypes.includes(type)) {
    return `请选择${name}`
  }

  return `请输入${name}`
}

export function splitInput(value) {
  if (!value) return []
  const list = []
  value.toString().split(/[\n|;|，|,|；]/)
    .forEach((text) => {
      const trimmed = text.trim()
      if (trimmed.length) {
        list.push(trimmed)
      }
    })
  return list
}

export function queryBuilderOperator(operator) {
  const operatorMap = {
    [QUERY_OPERATOR.EQ]: 'equal',
    [QUERY_OPERATOR.NE]: 'not_equal',
    [QUERY_OPERATOR.IN]: 'in',
    [QUERY_OPERATOR.NIN]: 'not_in',
    [QUERY_OPERATOR.GT]: 'greater',
    [QUERY_OPERATOR.LT]: 'less',
    [QUERY_OPERATOR.GTE]: 'greater_or_equal',
    [QUERY_OPERATOR.LTE]: 'less_or_equal',
    [QUERY_OPERATOR.LIKE]: 'contains',
    [QUERY_OPERATOR.CONTAINS]: 'contains',
    [QUERY_OPERATOR.CONTAINS_CS]: 'starts_with'
  }
  return operatorMap[operator] || operator.replace('$', '')
}

export function transformGeneralModelCondition(condition, properties) {
  const conditionIds = Object.keys(condition)
  if (!conditionIds.length) {
    return undefined
  }

  const conditions = { condition: 'AND', rules: [] }
  const timeCondition = { oper: 'and', rules: [] }

  for (let i = 0, id; id = conditionIds[i]; i++) {
    const property = properties.find(p => p.bk_property_id === id || p.id === id)
    if (!property) {
      continue
    }

    const { operator, value } = condition[id]

    if (value === null || value === undefined || !value.toString().length) {
      continue
    }

    if (property.bk_property_type === 'time') {
      const [start, end] = value
      timeCondition.rules.push({
        field: property.bk_property_id,
        start,
        end
      })
      continue
    }

    if (property.bk_property_type === 'date') {
      const [start, end] = value
      conditions.rules.push(
        { field: property.bk_property_id, operator: 'datetime_greater_or_equal', value: start },
        { field: property.bk_property_id, operator: 'datetime_less_or_equal', value: end }
      )
      continue
    }

    if (operator === QUERY_OPERATOR.RANGE) {
      const [start, end] = value
      conditions.rules.push(
        { field: property.bk_property_id, operator: queryBuilderOperator(QUERY_OPERATOR.GTE), value: start },
        { field: property.bk_property_id, operator: queryBuilderOperator(QUERY_OPERATOR.LTE), value: end }
      )
      continue
    }

    if (property.bk_property_type === 'map') {
      const tags = {}
      if (Array.isArray(value)) {
        value.forEach((val) => {
          if (typeof val === 'string') {
            const [k, v] = val.split('=')
            if (tags[k]) {
              tags[k].push(v)
            } else {
              tags[k] = [v]
            }
          }
        })

        const rules = []
        for (const [key, vals] of Object.entries(tags)) {
          rules.push({
            field: key,
            operator: queryBuilderOperator(operator),
            value: vals
          })
        }

        conditions.rules.push({
          field: property.bk_property_id,
          operator: 'filter_object',
          value: {
            condition: 'OR',
            rules
          }
        })
      }
      continue
    }

    const escapedValue = needEscapeOperator.includes(operator) ? value.replace(escapeCharRE, '\\$1') : value

    conditions.rules.push({
      field: property.bk_property_id,
      operator: queryBuilderOperator(operator),
      value: escapedValue
    })
  }

  return {
    conditions: conditions.rules.length ? conditions : undefined,
    time_condition: timeCondition.rules.length ? timeCondition : undefined
  }
}

export function resetConditionValue(conditionMap) {
  const newCondition = {}
  Object.keys(conditionMap).forEach((id) => {
    const propertyCondition = conditionMap[id]
    newCondition[id] = { ...propertyCondition }
    
    const value = getOperatorSideEffect(propertyCondition.property, newCondition[id].operator, [])
    newCondition[id].value = value
  })
  return newCondition
}

export default {
  getDefaultData,
  getOperatorSideEffect,
  convertValue,
  getPlaceholder,
  splitInput,
  queryBuilderOperator,
  transformGeneralModelCondition,
  resetConditionValue
}
