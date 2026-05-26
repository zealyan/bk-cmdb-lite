/**
 * RouterQuery - URL参数状态管理工具
 * 用于实现组件状态与URL参数的同步，支持页面刷新和前进后退时状态恢复
 */

const isEmpty = (value) => value === '' || value === undefined || value === null

const has = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key)

const deepEqual = (a, b) => {
  if (a === b) return true
  if (a === null || b === null) return false
  if (typeof a !== typeof b) return false
  if (typeof a !== 'object') return false

  const keysA = Object.keys(a)
  const keysB = Object.keys(b)
  if (keysA.length !== keysB.length) return false

  for (const key of keysA) {
    if (!keysB.includes(key)) return false
    if (!deepEqual(a[key], b[key])) return false
  }
  return true
}

const createWatchOptions = (key, options) => {
  const watchOptions = {
    immediate: false,
    deep: false
  }
  if (has(options, 'immediate')) {
    watchOptions.immediate = options.immediate
  }
  if (has(options, 'throttle')) {
    watchOptions.throttle = options.throttle
  }
  if (key === '*') {
    watchOptions.deep = true
  }
  return watchOptions
}

const createCallback = (keys, handler, options = {}) => {
  let immediateCalled = false

  const callback = (values, oldValues = {}) => {
    let execValue
    let execOldValue

    if (Array.isArray(keys)) {
      execValue = {}
      execOldValue = {}
      keys.forEach((key) => {
        execValue[key] = values[key]
        execOldValue[key] = oldValues[key]
      })
    } else if (keys === '*') {
      execValue = { ...values }
      execOldValue = { ...oldValues }
      if (has(options, 'ignore')) {
        const ignoreKeys = Array.isArray(options.ignore) ? options.ignore : [options.ignore]
        ignoreKeys.forEach((key) => {
          delete execValue[key]
          delete execOldValue[key]
        })
      }
    } else {
      execValue = values[keys]
      execOldValue = oldValues[keys]
    }

    if (options.immediate && !immediateCalled) {
      immediateCalled = true
      handler(execValue, execOldValue)
    } else {
      const hasChange = !deepEqual(execValue, execOldValue)
      if (hasChange) {
        handler(execValue, execOldValue)
      }
    }
  }

  if (has(options, 'throttle')) {
    const interval = typeof options.throttle === 'number' ? options.throttle : 100
    let lastCall = 0
    let timeoutId = null
    return (...args) => {
      const now = Date.now()
      const remaining = interval - (now - lastCall)
      if (remaining <= 0) {
        if (timeoutId) {
          clearTimeout(timeoutId)
          timeoutId = null
        }
        lastCall = now
        callback(...args)
      } else if (!timeoutId) {
        timeoutId = setTimeout(() => {
          lastCall = Date.now()
          timeoutId = null
          callback(...args)
        }, remaining)
      }
    }
  }

  return callback
}

class RouterQuery {
  constructor () {
    this.router = null
    this.vueApp = null
  }

  setRouter (router) {
    this.router = router
  }

  setVueApp (app) {
    this.vueApp = app
  }

  get route () {
    if (!this.router) return null
    return this.router.currentRoute
  }

  get (key, defaultValue) {
    const route = this.route
    if (!route) return defaultValue

    const value = route.query[key]
    if (value !== undefined) {
      return value
    }
    return arguments.length > 1 ? defaultValue : null
  }

  getAll () {
    const route = this.route
    return route ? { ...route.query } : {}
  }

  set (key, value) {
    if (!this.router) return

    const route = this.route
    if (!route) return

    const query = { ...route.query }

    if (typeof key === 'object') {
      Object.assign(query, key)
    } else {
      query[key] = value
    }

    Object.keys(query).forEach(queryKey => {
      if (isEmpty(query[queryKey])) {
        delete query[queryKey]
      }
    })

    this.router.replace({
      ...route,
      query
    })
  }

  setAll (query) {
    if (!this.router) return

    const route = this.route
    if (!route) return

    this.router.replace({
      ...route,
      query: { ...query }
    })
  }

  delete (key) {
    if (!this.router) return

    const route = this.route
    if (!route) return

    const query = { ...route.query }
    delete query[key]

    this.router.replace({
      ...route,
      query
    })
  }

  refresh () {
    this.set('_t', Date.now())
  }

  clear () {
    if (!this.router) return

    const route = this.route
    if (!route) return

    this.router.replace({
      ...route,
      query: {}
    })
  }

  getAs (key, type, defaultValue) {
    const value = this.get(key)
    if (value === null || value === undefined) return defaultValue

    switch (type) {
      case 'int':
        return parseInt(value, 10) || defaultValue
      case 'float':
        return parseFloat(value) || defaultValue
      case 'bool':
        return value === 'true' || value === '1'
      default:
        return value
    }
  }

  watch (key, handler, options = {}) {
    if (!this.vueApp) {
      console.warn('[RouterQuery] watch() requires Vue app instance. Call setVueApp() first.')
      return () => {}
    }

    const watchOptions = createWatchOptions(key, options)
    const callback = createCallback(key, handler, options)
    const expression = () => this.route ? this.route.query : {}

    const stopWatch = this.vueApp.$watch(expression, callback, {
      immediate: watchOptions.immediate,
      deep: watchOptions.deep
    })

    return stopWatch
  }

  watchImmediate (key, handler, options = {}) {
    return this.watch(key, handler, { ...options, immediate: true })
  }

  watchThrottle (key, handler, interval = 100) {
    return this.watch(key, handler, { throttle: interval })
  }
}

const routerQuery = new RouterQuery()

export const initRouterQuery = (router, app = null) => {
  routerQuery.setRouter(router)
  if (app) {
    routerQuery.setVueApp(app)
  }
}

export default routerQuery
