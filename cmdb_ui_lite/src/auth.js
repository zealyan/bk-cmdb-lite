/**
 * 最小内置鉴权前端核心
 * - token 存 localStorage（键名 lite_bk_token，本 lite 自定义名，规避上游/网关对 bk_token 的处理），
 *   同时写同名 lite_bk_token cookie；用户名缓存键为 lite_bk_user_name。
 * - ensureAuth()：首次导航时调 /api/v1/auth/me 判定登录态，结果缓存复用
 * - loadAuthConfig()：拉取后端鉴权配置（Authorization: Bearer 开关等），供请求拦截器决策承载方式
 * - 不做导航栏 selector 切换器（按需求不实现）
 */
import { me, getAuthConfig, renew } from '@/api/auth'
import { handleApiError, AUTH_ERR_UNAUTHORIZED } from '@/utils/error-handler'
import { AUTH_RECHECK_MS, ACTIVITY_WINDOW_MS } from '@/config'

const TOKEN_KEY = 'lite_bk_token'
const USER_KEY = 'lite_bk_user_name'
const SKIP_KEY = 'cmdb_skip_login'
const BEARER_KEY = 'cmdb_auth_bearer'
const TOKEN_QUERY_KEY = 'cmdb_auth_token_query'

// 会话心跳 / 续期 / 活跃窗口参数集中在 `@/config`，此处仅引用，不再本地硬编码。

let _pending = null
let _resolved = null
let _resolvedAt = 0
// 防重入：一次会话失效只触发一次「提示 + 跳登录」，避免并发请求风暴引发多次跳转
let _expiring = false
// 会话心跳定时器：周期性调 /me 检出「停留页面不动」时的静默超时
let _watchTimer = null

// ── 活跃触发续期状态 ──
let _lastActivity = 0   // 最近一次用户交互时刻
let _lastRenew = 0      // 最近一次成功续期时刻（节流用）
let _activityBound = false
const _ACTIVITY_EVENTS = ['mousemove', 'keydown', 'click', 'touchstart']
function _onActivity() {
  _lastActivity = Date.now()
}
function _bindActivity() {
  if (_activityBound) return
  _ACTIVITY_EVENTS.forEach((ev) => window.addEventListener(ev, _onActivity, { passive: true }))
  _activityBound = true
  _lastActivity = Date.now()
}
function _unbindActivity() {
  if (!_activityBound) return
  _ACTIVITY_EVENTS.forEach((ev) => window.removeEventListener(ev, _onActivity))
  _activityBound = false
}

// 历史命名兼容迁移：把旧 'bk_token' / 'bk_user_name' 自动迁移到 lite_ 前缀键，
// 并清除旧键，避免已登录用户的浏览器缓存（localStorage）因改名而失效 / 残留。
// 幂等：仅在旧键存在、且新键尚不存在时才复制；每次加载都执行，无副作用。
;(function _migrateLegacyCacheKeys() {
  const legacy = [
    ['bk_token', TOKEN_KEY],
    ['bk_user_name', USER_KEY],
  ]
  for (const [oldK, newK] of legacy) {
    const v = localStorage.getItem(oldK)
    if (v != null && localStorage.getItem(newK) == null) {
      localStorage.setItem(newK, v)
    }
    localStorage.removeItem(oldK)
  }
})()

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function getBearerEnabled() {
  // 后端默认 AUTH_BEARER=false（关闭）；未拉取到配置前也按关闭处理，
  // 待 loadAuthConfig 写入 '1'/'0' 后为准。避免 share-link 网关污染 Authorization 头。
  return localStorage.getItem(BEARER_KEY) === '1'
}

export function getTokenQueryEnabled() {
  // 后端默认 AUTH_TOKEN_QUERY=false（关闭）；未拉取到配置前按关闭处理，
  // 避免 token 进入 URL query（泄露面：代理日志 / 浏览器历史 / Referer）。
  return localStorage.getItem(TOKEN_QUERY_KEY) === '1'
}

/**
 * 拉取后端鉴权配置并缓存（auth_bearer / auth_token_query 开关等）。
 * 由 ensureAuth() 在首次导航时调用，供 client.js 拦截器同步读取。
 */
export async function loadAuthConfig() {
  try {
    const cfg = await getAuthConfig()
    // 后端下发的开关原样落 localStorage：'1'=开，'0'=关（默认关闭）。
    localStorage.setItem(BEARER_KEY, cfg && cfg.auth_bearer ? '1' : '0')
    localStorage.setItem(TOKEN_QUERY_KEY, cfg && cfg.auth_token_query ? '1' : '0')
    return cfg
  } catch (e) {
    return null
  }
}

export function setToken(t) {
  localStorage.setItem(TOKEN_KEY, t)
  document.cookie = `lite_bk_token=${t}; path=/; max-age=3600`
  _resolved = null   // 登录后重置缓存，下次导航重新校验
  _resolvedAt = 0
  _pending = null
  startSessionWatch()  // 登录成功即开始会话心跳，及时检出静默超时
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  document.cookie = 'lite_bk_token=; path=/; max-age=0'
  _resolved = null
  _resolvedAt = 0
  _pending = null
  stopSessionWatch()   // 退出登录 / 会话失效后停止心跳
}

/**
 * 会话心跳（兼 keep-alive 续期）：
 * - 用户「活跃」（距上次交互 ≤ ACTIVITY_WINDOW_MS）：调 /renew 重签 token 并写回，
 *   使有效期相对当前时刻滚动（sliding session）→ 实现「使用时保活」。
 * - 用户「闲置」：仅调 /me 做超时检测，不续期，会话照常到期。
 * - /renew 或 /me 返回 1302100（已过期）：响应拦截器统一处理（弹提示 + 跳登录页带回跳）。
 * - 系统层错误（网络/5xx 瞬时抖动）：不强制跳登录，避免误伤。
 * 幂等：重复调用只保留一个定时器 + 一组事件监听。
 */
function startSessionWatch() {
  if (_watchTimer) return
  _bindActivity()
  _watchTimer = setInterval(async () => {
    const now = Date.now()
    try {
      if (now - _lastActivity <= ACTIVITY_WINDOW_MS) {
        // 活跃：续期（重签 token，滑动有效期）；同时兼任超时检测
        const info = await renew()
        if (info && info.bk_token) {
          setToken(info.bk_token) // 写回新 token（含 cookie），滑动会话
          _lastRenew = now
        }
      } else {
        // 闲置：仅做超时检测，不续期（让会话照常到期）
        await me()
      }
    } catch (e) {
      // 1302100 由响应拦截器统一跳转；其它错误静默忽略（瞬时抖动）。
    }
  }, AUTH_RECHECK_MS)
}

function stopSessionWatch() {
  if (_watchTimer) {
    clearInterval(_watchTimer)
    _watchTimer = null
  }
  _unbindActivity()
}

export function getUserName() {
  return localStorage.getItem(USER_KEY) || ''
}

export function setUserName(name) {
  if (name) {
    localStorage.setItem(USER_KEY, name)
  } else {
    localStorage.removeItem(USER_KEY)
  }
}

export function getSkipLogin() {
  return localStorage.getItem(SKIP_KEY) === '1'
}

function setSkipLogin(v) {
  localStorage.setItem(SKIP_KEY, v ? '1' : '0')
}

/**
 * 判定当前是否已登录 / 是否 skipLogin。
 * 返回 Promise<boolean>：true=可进入应用，false=需跳登录页。
 */
export function ensureAuth() {
  const now = Date.now()
  // 复检节流：结果未过期（< AUTH_RECHECK_MS）直接复用，避免每次导航都打 /me；
  // 过期后再导航/API 才重新校验，从而能及时检出 token 静默超时。
  if (_resolved !== null && now - _resolvedAt < AUTH_RECHECK_MS) {
    return Promise.resolve(_resolved)
  }
  if (_pending) return _pending
  // 必须先拉取后端鉴权配置（auth_bearer / auth_token_query 开关），再发 /me：
  // 拦截器按这些开关决定承载方式，若并发执行可能让首个 /me 落在默认值上、携带错误载荷。
  _pending = loadAuthConfig()
    .then(() => me())
    .then((info) => {
      if (info && info.skipLogin) {
        setSkipLogin(true)
        _resolved = true
        return true
      }
      setSkipLogin(false)
      if (info && info.bk_user_name) {
        _resolved = true
        return true
      }
      _resolved = false
      return false
    })
    .catch((e) => {
      setSkipLogin(false)
      const code = e && e.bk_error_code
      if (code === AUTH_ERR_UNAUTHORIZED) {
        // 业务层：之前持 token 但校验失败（过期 / 被网关注入污染 / 签名不符）→
        // 提示「登录已失效」引导重新登录；首次进入无 token 的常规未登录不弹窗，直接跳登录页。
        if (getToken()) {
          handleApiError(e)
        }
      } else {
        // 系统层：网络中断 / 后端 5xx / 网关异常 / 代理 502 → 统一提示，
        // 避免「登录无反应、静默跳回登录页」却无任何 UI 解释。
        handleApiError(e)
      }
      _resolved = false
      return false
    })
    .finally(() => { _resolvedAt = Date.now(); _pending = null })
  return _pending
}

/**
 * 会话失效统一处理：登录超时（1302100）/ 被踢 / 签名不符等。
 * 1) UI 提示（复用项目公共 handleApiError，走 bk-message）；
 * 2) 清除本地 token，避免循环重试；
 * 3) 跳转登录页并携带当前路由作为回跳参数（登录成功后由 login 页 redirectTarget 消费），
 *    用户重新登录即可回到原页面。
 * 防御：若当前已在登录页（或其 URL 已含 redirect 参数），先抽取内层 redirect 作为目标，
 * 杜绝「登录 → 跳登录 → 再跳登录」的嵌套/死循环；目标与当前一致时不再改写 hash。
 * 仅在「已持有过 token」的会话场景调用；首次进入无 token 的常规未登录不弹窗、不跳（由路由守卫静默处理）。
 * @param {string} [reason] 提示文案；缺省使用中性默认语
 */
export function redirectToLogin(reason) {
  if (_expiring) return
  _expiring = true
  try {
    const msg = (reason && String(reason).trim()) || '登录状态已失效，请重新登录'
    handleApiError({ bk_error_code: AUTH_ERR_UNAUTHORIZED, bk_error_msg: msg })
  } catch (e) {
    // 提示失败不应阻断跳转
  }
  // 清 token + 重置复检缓存：下次进入需重新登录校验
  clearToken()
  // 计算回跳目标（hash 模式：location.hash 形如 #/business/2/index）
  let current = window.location.hash.slice(1) || '/index'
  // 当前已在登录页（含其自身 redirect 参数）：抽取内层 redirect 作目标，避免嵌套/死循环
  if (current.startsWith('/login')) {
    try {
      const q = new URLSearchParams(current.split('?')[1] || '')
      const inner = q.get('redirect')
      current = (inner && inner.startsWith('/') && inner !== '/login') ? inner : '/index'
    } catch (e) {
      current = '/index'
    }
  }
  const target = `#/login?redirect=${encodeURIComponent(current)}`
  // 目标与当前一致（如已在干净登录页）则不改写 hash，避免无意义刷新/循环
  if (window.location.hash !== target) {
    window.location.hash = target
  }
  // 防重入解锁（避免并发请求风暴引发多次跳转）
  setTimeout(() => { _expiring = false }, 1500)
}
