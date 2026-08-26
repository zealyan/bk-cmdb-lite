/**
 * 统一后端业务错误的 UI 呈现（对齐上游蓝鲸 CMDB 的「无权限」处理）。
 *
 * 设计目标：
 *  - 无权限（bk_error_code === 1302102）：全网统一弹出「无操作权限」对话框，
 *    且同一时刻只弹一个，绝不回退到“异常 / 错误”等兜底层级文案。
 *  - 其余业务错误：直接展示后端返回的 bk_error_msg（已由后端给出可读原因），
 *    兜底文案中禁止出现“异常 / 错误”等兜底层级字眼。
 *
 * 接入方式：
 *  - main.js 启动时调用 bindMagic(app) 注入 bkMagic 实例（提供 $bkInfo / $bkMessage）。
 *  - 各组件 catch 中调用 this.$handleApiError(error)（已挂 Vue.prototype）。
 *  - src/api/client.js 响应拦截器对 1302102 全局兜底弹窗，并打 error.handled 标记，
 *    组件层再次进入 handleApiError 时发现已处理则跳过，避免重复弹窗。
 */

export const NO_PERMISSION_CODE = 1302102
export const NO_PERMISSION_MSG = '无操作权限'

// 鉴权相关错误码（与后端 app/config/settings.py 的 AUTH_ERR_* 保持一致）
export const AUTH_ERR_UNAUTHORIZED = 1302100   // 未登录 / 登录失效（/me 返回）
export const AUTH_ERR_BAD_CREDENTIAL = 1302101 // 用户名或密码错误（/login 返回）

// 后端 Action 枚举常量（见 app/auth/resource.py），用于把无权限载荷翻译为中文动作名
const ACTION_LABEL = {
  create: '创建',
  update: '编辑',
  delete: '删除',
  find: '查看'
}

let _magic = null

export function bindMagic(instance) {
  _magic = instance
}

function getMagic(vm) {
  if (vm && vm.$bkInfo && vm.$bkMessage) return vm
  return _magic
}

// 把后端 permission 载荷翻译成可读的「缺少权限」描述
function describePermission(permission) {
  const list = (permission && permission.permissions) || []
  if (!list.length) return ''
  return list
    .map(p => {
      const act = ACTION_LABEL[p.action] || p.action || ''
      const obj = p.obj_id || ''
      return `「${obj}」模型的「${act}」操作`
    })
    .join('；')
}

// 同一时刻只保留一个无权限弹窗，避免并发请求时叠罗汉
let _showing = false

function resetShowing() {
  _showing = false
}

/**
 * 统一「无操作权限」弹窗。
 * @param {Error} error 响应拦截器抛出的业务错误，error.response.data 含 permission 载荷
 */
export function showNoPermission(error) {
  const magic = getMagic()
  if (!magic || _showing) return

  const data = (error && error.response && error.response.data) || {}
  const permission = data.permission || null
  const detail = describePermission(permission)

  const lines = ['当前账号没有执行该操作的权限。']
  if (detail) lines.push(`缺少权限：${detail}`)
  lines.push('如需访问，请联系管理员申请相应权限。')

  _showing = true
  // bkMagic Info 组件支持 theme / title / subTitle / okText / confirmFn，
  // subTitle 以 white-space:pre 渲染，\n 可换行。
  magic.$bkInfo({
    title: '无操作权限',
    subTitle: lines.join('\n'),
    theme: 'danger',
    okText: '我知道了',
    confirmFn: resetShowing
  })
  // 用户点右上角 X 关闭时不触发 confirmFn，用定时器兜底解锁
  setTimeout(resetShowing, 4000)
}

/**
 * 系统层错误（网络 / 5xx / 4xx / 3xx / 网关）文案。按项目「异常返回规则」，
 * 兜底文案禁止出现“异常 / 错误”等兜底层级字眼，故用中性、可操作的中文描述。
 *
 * 与后端 HTTP_STATUS_ERROR_META（app/utils/exceptions.py http_error_meta）
 * 文案保持一致：正常链路下后端已把 HTTP 异常统一为 BaseResp + HTTP 200，
 * 由 handleApiError 直接展示 bk_error_msg；本映射仅兜底「后端不可达 /
 * debug 模式原始 500 / 网关注入的非 2xx」等残留场景，避免用户看到
 * “Request failed with status code 405”这类传输层文案。
 *
 * @param {Error} error
 * @returns {string} 系统层提示文案；未识别状态返回 ''
 */
const HTTP_STATUS_MSG = {
  304: '请求已被缓存，请刷新页面后重试',
  400: '请求参数有误，请检查后重试',
  401: '未认证或登录已失效，请重新登录',
  403: '没有访问该资源的权限',
  404: '请求路径不存在',
  405: '请求方式不被支持',
  408: '请求超时，请稍后重试',
  413: '请求体过大，请精简后重试',
  415: '不支持的媒体类型',
  429: '请求过于频繁，请稍后重试'
}

function resolveSystemMessage(error) {
  // 网络层：无响应体（断网 / DNS / CORS / 网关完全不可达）
  if (!error || !error.response) {
    return '网络连接失败，请检查网络后重试'
  }
  const status = error.response.status
  if (status >= 500) {
    return '服务暂时不可用，请稍后重试'
  }
  // 3xx（重定向 / 304 缓存命中被 axios 判为非 2xx）与已单列的 4xx 细分提示
  if (status >= 300 && status < 400) {
    return '请求被重定向，请刷新后重试'
  }
  return HTTP_STATUS_MSG[status] || ''
}

/**
 * 集中处理任意 API 业务错误。
 * - 1302102：走统一无权限弹窗（已弹过的去重）。
 * - 业务错误（有 bk_error_msg）：直接展示后端可读原因。
 * - 系统层错误（无响应 / 5xx）：展示中性、可操作的提示，绝不出现“异常 / 错误”字眼。
 * - 其它：通用兜底“操作未成功，请稍后重试”。
 * @param {Error} error
 * @param {Object} [vm] 组件实例（可选，缺省回退到 bindMagic 注入的实例）
 */
export function handleApiError(error, vm) {
  if (!error) return
  // 已被集中处理器（响应拦截器 / 会话失效跳转）标记 handled 的错误不再重复弹窗，
  // 避免 1302100/1302102 在中层拦截器已提示后，组件 catch 再次弹出。
  if (error.handled) return

  const code =
    error.bk_error_code ||
    (error.response && error.response.data && error.response.data.bk_error_code)
  if (code === NO_PERMISSION_CODE) {
    if (!error.handled) showNoPermission(error)
    return
  }

  const magic = getMagic(vm)
  if (!magic) return

  // 优先用后端给出的业务消息（bk_error_msg）；业务消息缺失时，区分系统层错误给出中性提示。
  // 后端业务消息一律原样展示（即便含“错误”二字，如“用户名或密码错误”，属具体可读原因）。
  const businessMsg =
    error.bk_error_msg ||
    (error.response && error.response.data && error.response.data.bk_error_msg) ||
    ''
  let msg = businessMsg
  let isBusiness = !!businessMsg
  if (!msg) {
    const sysMsg = resolveSystemMessage(error)
    msg = sysMsg || error.message || ''
    isBusiness = false
  }

  // 兜底：仅当「无后端业务消息」且消息本身属于兜底层级文案时，才替换为中性提示，
  // 避免把“异常 / 错误”等兜底层级字眼暴露给用户。
  if (!isBusiness && (!msg || /请求处理未完成|请求处理失败|未知错误|业务处理失败|服务器内部错误|Network Error|Request failed/.test(msg))) {
    msg = '操作未成功，请稍后重试'
  }

  magic.$bkMessage({ theme: 'error', message: msg })
}
