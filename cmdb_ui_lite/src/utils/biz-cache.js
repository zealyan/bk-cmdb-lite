/**
 * 业务 ID 缓存（按用户作用域）
 * ------------------------------------------------------------------
 * 业务路由（业务拓扑 / 业务主机详情）的入口在菜单定义里默认使用占位 bizId=0，
 * 而 0 不是一个真实存在的业务，会导致首屏进入 /#/business/0/index 后页面
 * 无法加载、导航栏业务选择器也无法匹配任何选项。
 *
 * 这里提供一套「业务 ID 默认缓存」机制：
 *  - 优先读取「当前用户」最近一次选择的业务（localStorage 按用户持久化，跨会话保留）；
 *  - 未缓存时回退到 DEFAULT_BIZ_ID（蓝鲸平台 = 2，与路由默认重定向一致）。
 *
 * 与原项目 bk-cmdb 的关系：
 *  原项目 src/ui/src/router/business-interceptor.js 用固定键
 *  `window.localStorage.setItem('selectedBusiness', id)` 做全局缓存，
 *  【该键不带用户前缀，所有用户共享同一份，非用户范围】。
 *  本 lite 在「复刻」该 localStorage 思路的基础上，将键名改造为按用户隔离：
 *  `selectedBusiness_<userName>`，从而做到「每个用户记住各自上次业务」，
 *  避免多用户（如 admin / tom）在同一浏览器互相覆盖选中业务。
 *
 * 兼容性：无用户名（免登录 / 未识别身份）时回落旧版全局键 `selectedBusiness`，
 * 保证 skipLogin=admin 等场景与历史数据不丢失。
 */

// 原项目 bk-cmdb 的全局键（仅作无用户名时的向后兼容回落，不再主动写入）
const LEGACY_KEY = 'selectedBusiness'

// 按用户隔离的键：selectedBusiness_<userName>
const userStorageKey = (userName) => `selectedBusiness_${userName}`

// 与 router 默认重定向（/business/2/index）保持一致
export const DEFAULT_BIZ_ID = 2

function safeStorage() {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage
    }
  } catch (e) { /* 隐私模式 / 禁用 storage 时静默降级 */ }
  return null
}

/**
 * 读取当前用户缓存的业务 ID（用户范围）
 * @param {string} userName 当前登录用户名；为空时回落旧版全局键
 * @param {number|string} fallback 无缓存时的回退值，默认 DEFAULT_BIZ_ID
 * @returns {string} 业务 ID（字符串）
 */
export function getCachedBizId(userName = '', fallback = DEFAULT_BIZ_ID) {
  const storage = safeStorage()
  if (storage) {
    try {
      if (userName) {
        // 1) 当前用户专属键（用户范围，优先）
        const u = storage.getItem(userStorageKey(userName))
        if (u !== null && u !== '') {
          const n = Number(u)
          if (!Number.isNaN(n) && n > 0) return String(n)
        }
      } else {
        // 2) 无用户名（免登录 / 未识别）：回落旧版全局键，保持向后兼容
        const g = storage.getItem(LEGACY_KEY)
        if (g !== null && g !== '') {
          const n = Number(g)
          if (!Number.isNaN(n) && n > 0) return String(n)
        }
      }
    } catch (e) { /* ignore */ }
  }
  return String(fallback)
}

/**
 * 写入当前用户缓存的业务 ID（用户范围）
 * @param {number|string} bizId 业务 ID
 * @param {string} userName 当前登录用户名；为空时回落旧版全局键
 */
export function setCachedBizId(bizId, userName = '') {
  if (bizId === undefined || bizId === null || bizId === '') return
  const n = Number(bizId)
  if (Number.isNaN(n) || n <= 0) return
  const storage = safeStorage()
  if (storage) {
    try {
      // 写入当前用户专属键（用户范围）；无用户名时回落全局键
      const key = userName ? userStorageKey(userName) : LEGACY_KEY
      storage.setItem(key, String(n))
    } catch (e) { /* ignore */ }
  }
}

/**
 * 清除缓存的业务 ID
 * @param {string} userName 当前登录用户名；为空时清除旧版全局键
 */
export function clearCachedBizId(userName = '') {
  const storage = safeStorage()
  if (storage) {
    try {
      if (userName) {
        storage.removeItem(userStorageKey(userName))
      } else {
        storage.removeItem(LEGACY_KEY)
      }
    } catch (e) { /* ignore */ }
  }
}
