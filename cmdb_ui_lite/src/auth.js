/**
 * 最小内置鉴权前端核心
 * - token 存 localStorage（SPA 习惯），同时写 bk_token cookie 对齐上游透传形状
 * - ensureAuth()：首次导航时调 /api/v1/auth/me 判定登录态，结果缓存复用
 * - 不做导航栏 selector 切换器（按需求不实现）
 */
import { me } from '@/api/auth'

const TOKEN_KEY = 'bk_token'
const SKIP_KEY = 'cmdb_skip_login'

let _pending = null
let _resolved = null

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(t) {
  localStorage.setItem(TOKEN_KEY, t)
  document.cookie = `bk_token=${t}; path=/; max-age=3600`
  _resolved = null   // 登录后重置缓存，下次导航重新校验
  _pending = null
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
  document.cookie = 'bk_token=; path=/; max-age=0'
  _resolved = null
  _pending = null
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
  if (_resolved !== null) return Promise.resolve(_resolved)
  if (_pending) return _pending
  _pending = me()
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
    .catch(() => {
      setSkipLogin(false)
      _resolved = false
      return false
    })
    .finally(() => { _pending = null })
  return _pending
}
