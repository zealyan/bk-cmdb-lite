/**
 * 业务 ID 默认全局缓存
 * ------------------------------------------------------------------
 * 业务路由（业务拓扑 / 业务主机详情）的入口在菜单定义里默认使用占位 bizId=0，
 * 而 0 不是一个真实存在的业务，会导致首屏进入 /#/business/0/index 后页面
 * 无法加载、导航栏业务选择器也无法匹配任何选项。
 *
 * 这里提供一套「全局默认业务 ID」机制：
 *  - 优先读取用户最近一次选择的业务（localStorage 持久化，跨会话保留）；
 *  - 未缓存时回退到 DEFAULT_BIZ_ID（蓝鲸平台 = 2，与路由默认重定向一致）。
 *
 * 通过 setCachedBizId 在用户切换业务 / 进入业务路由时写入，实现「默认全局保存」。
 */

// 与原项目 bk-cmdb 保持一致：业务 ID 持久化键名使用 'selectedBusiness'
// （原项目 src/ui/src/router/business-interceptor.js: window.localStorage.setItem('selectedBusiness', id)）
const BIZ_ID_STORAGE_KEY = 'selectedBusiness'

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

export function getCachedBizId(fallback = DEFAULT_BIZ_ID) {
  const storage = safeStorage()
  if (storage) {
    try {
      const raw = storage.getItem(BIZ_ID_STORAGE_KEY)
      if (raw !== null && raw !== '') {
        const n = Number(raw)
        if (!Number.isNaN(n) && n > 0) {
          return String(n)
        }
      }
    } catch (e) { /* ignore */ }
  }
  return String(fallback)
}

export function setCachedBizId(bizId) {
  if (bizId === undefined || bizId === null || bizId === '') return
  const n = Number(bizId)
  if (Number.isNaN(n) || n <= 0) return
  const storage = safeStorage()
  if (storage) {
    try {
      storage.setItem(BIZ_ID_STORAGE_KEY, String(n))
    } catch (e) { /* ignore */ }
  }
}

export function clearCachedBizId() {
  const storage = safeStorage()
  if (storage) {
    try {
      storage.removeItem(BIZ_ID_STORAGE_KEY)
    } catch (e) { /* ignore */ }
  }
}
