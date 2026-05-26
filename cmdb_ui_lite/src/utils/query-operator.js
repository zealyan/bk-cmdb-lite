export const QUERY_OPERATOR = Object.freeze({
  EQ: '$eq',
  NE: '$ne',
  IN: '$in',
  NIN: '$nin',
  LT: '$lt',
  GT: '$gt',
  LTE: '$lte',
  GTE: '$gte',
  RANGE: '$range',
  NRANGE: '$nrange',
  LIKE: '$regex',
  CONTAINS: '$contains',
  CONTAINS_CS: '$contains_s'
})

export const QUERY_OPERATOR_SYMBOL = {
  [QUERY_OPERATOR.EQ]: '=',
  [QUERY_OPERATOR.NE]: '≠',
  [QUERY_OPERATOR.IN]: 'in',
  [QUERY_OPERATOR.NIN]: 'not in',
  [QUERY_OPERATOR.GT]: '>',
  [QUERY_OPERATOR.LT]: '<',
  [QUERY_OPERATOR.GTE]: '≥',
  [QUERY_OPERATOR.LTE]: '≤',
  [QUERY_OPERATOR.LIKE]: 'like',
  [QUERY_OPERATOR.RANGE]: '≤ ≥',
  [QUERY_OPERATOR.CONTAINS]: 'contains',
  [QUERY_OPERATOR.CONTAINS_CS]: 'contains(CS)'
}

export const QUERY_OPERATOR_DESC = {
  [QUERY_OPERATOR.EQ]: '等于',
  [QUERY_OPERATOR.NE]: '不等于',
  [QUERY_OPERATOR.LT]: '小于',
  [QUERY_OPERATOR.GT]: '大于',
  [QUERY_OPERATOR.IN]: '包含在',
  [QUERY_OPERATOR.NIN]: '不包含在',
  [QUERY_OPERATOR.RANGE]: '数值范围',
  [QUERY_OPERATOR.LTE]: '小于等于',
  [QUERY_OPERATOR.GTE]: '大于等于',
  [QUERY_OPERATOR.LIKE]: '模糊',
  [QUERY_OPERATOR.CONTAINS]: '匹配(大小写不敏感)',
  [QUERY_OPERATOR.CONTAINS_CS]: '匹配(大小写敏感)'
}

export function getOperatorSymbol(operator) {
  return QUERY_OPERATOR_SYMBOL[operator] || operator.replace('$', '')
}

export function getOperatorDesc(operator) {
  return QUERY_OPERATOR_DESC[operator] || operator.replace('$', '')
}

export default {
  QUERY_OPERATOR,
  QUERY_OPERATOR_SYMBOL,
  QUERY_OPERATOR_DESC,
  getOperatorSymbol,
  getOperatorDesc
}
