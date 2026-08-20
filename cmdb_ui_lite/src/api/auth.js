/**
 * 鉴权相关 API
 * 依赖 src/api/client.js 的响应拦截器：成功时返回 data.data（内层），
 * 失败时抛出带 bk_error_msg / bk_error_code 的异常。
 */
import http from './client'

export function login(data) {
  return http.post('/api/v1/auth/login', data)
}

export function me() {
  return http.get('/api/v1/auth/me')
}

export function getAuthConfig() {
  return http.get('/api/v1/auth/config')
}

export function logout() {
  return http.post('/api/v1/auth/logout')
}

export function renew() {
  return http.post('/api/v1/auth/renew')
}
