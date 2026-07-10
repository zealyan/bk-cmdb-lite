import { QUERY_OPERATOR } from '@/utils/query-operator'
import { transformGeneralModelCondition } from '@/components/filter/utils'

const defaultFastQuery = () => ({
  field: '',
  filter: '',
  operator: '',
  fuzzy: ''
})

const defaultBaseQuery = () => ({
  page: '',
  _t: Date.now()
})

export function setSearchQueryByCondition(conditionMap = {}, properties = []) {
  const params = new URLSearchParams(window.location.search)
  const filterAdvStr = params.get('filter_adv') || ''
  const query = filterAdvStr ? JSON.parse(decodeURIComponent(filterAdvStr)) : {}
  const field = params.get('field')
  let clearFastQuery = {}

  Object.keys(conditionMap).forEach((id) => {
    const { operator, value } = conditionMap[id]
    const key = `${id}.${operator.replace('$', '')}`

    if (String(value).length) {
      if (Array.isArray(value)) {
        query[key] = value.join(',')
      } else {
        query[key] = value
      }

      const property = properties.find(p => p.bk_property_id === id || p.id === id)
      if (property && field === property.bk_property_id) {
        clearFastQuery = defaultFastQuery()
      }
    } else if (Reflect.has(query, key)) {
      Reflect.deleteProperty(query, key)
    }
  })

  Object.keys(query).forEach((key) => {
    const [id] = key.split('.')
    if (!conditionMap[id]) {
      Reflect.deleteProperty(query, key)
    }
  })

  const newParams = new URLSearchParams()
  if (Object.keys(query).length > 0) {
    newParams.set('filter_adv', encodeURIComponent(JSON.stringify(query)))
  }
  newParams.set('s', 'adv')
  newParams.set('_t', Date.now().toString())

  Object.keys(clearFastQuery).forEach(key => {
    if (clearFastQuery[key]) {
      newParams.set(key, clearFastQuery[key])
    }
  })

  const newUrl = `${window.location.pathname}?${newParams.toString()}`
  window.history.pushState({}, '', newUrl)

  return newUrl
}

export function parseSearchQueryFromUrl() {
  const params = new URLSearchParams(window.location.search)
  const filterAdvStr = params.get('filter_adv')
  const searchType = params.get('s')

  if (!filterAdvStr || !searchType) {
    return { conditions: {}, searchType }
  }

  try {
    const query = JSON.parse(decodeURIComponent(filterAdvStr))
    const conditions = {}

    Object.keys(query).forEach((key) => {
      const [id, operator] = key.split('.')
      const value = query[key].toString()

      conditions[id] = {
        operator: `$${operator}`,
        value: value
      }
    })

    return { conditions, searchType }
  } catch (error) {
    console.error('解析查询参数失败:', error)
    return { conditions: {}, searchType }
  }
}

export function buildSearchParams(condition, properties, options = {}) {
    const { page = 1, pageSize = 10, sort = '-id' } = options

    const params = {
        page: page,
        page_size: pageSize,
        sort: sort
    }

    // 属性类型映射，用于判断 date/time 类型
    const propertyMap = {}
    if (Array.isArray(properties)) {
        properties.forEach(p => {
            propertyMap[p.bk_property_id] = p
        })
    }

    // 处理所有条件，支持多条件AND组合查询
    const conditionIds = Object.keys(condition)
    if (conditionIds.length > 0) {
        const conditions = []

        conditionIds.forEach(fieldId => {
            const { operator, value } = condition[fieldId]

            // 跳过空值
            if (value === undefined || value === null || (typeof value === 'string' && value.length === 0)) {
                return
            }

            // 跳过空数组
            if (Array.isArray(value) && value.length === 0) {
                return
            }

            const property = propertyMap[fieldId]
            const propertyType = property ? property.bk_property_type : ''

            // $range 操作符拆分（与原项目一致）
            if (operator === '$range' || operator === '$nrange') {
                const rangeValues = Array.isArray(value) ? value : String(value).split(/[\n,，;；]/).filter(v => v.trim().length)
                if (rangeValues.length >= 2) {
                    if (operator === '$range') {
                        conditions.push({ field: fieldId, operator: '$gte', value: rangeValues[0], fuzzy: false })
                        conditions.push({ field: fieldId, operator: '$lte', value: rangeValues[1], fuzzy: false })
                    } else {
                        conditions.push({ field: fieldId, operator: '$nrange', value: [rangeValues[0], rangeValues[1]], fuzzy: false })
                    }
                } else if (rangeValues.length === 1 && operator === '$range') {
                    conditions.push({ field: fieldId, operator: '$gte', value: rangeValues[0], fuzzy: false })
                }
                return
            }

            const cond = {
                field: fieldId,
                operator: operator,
                fuzzy: operator === '$regex' || operator === '$like'
            }

            cond.value = value

            conditions.push(cond)
        })

        if (conditions.length > 0) {
            params.conditions = conditions
        }
    }

    return params
}

export function clearSearchQuery() {
  const newParams = new URLSearchParams()
  newParams.set('_t', Date.now().toString())

  const newUrl = `${window.location.pathname}?${newParams.toString()}`
  window.history.pushState({}, '', newUrl)

  return newUrl
}

export default {
  setSearchQueryByCondition,
  parseSearchQueryFromUrl,
  buildSearchParams,
  clearSearchQuery
}
