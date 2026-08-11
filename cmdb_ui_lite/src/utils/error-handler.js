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
 * 集中处理任意 API 业务错误。
 * - 1302102：走统一无权限弹窗（已弹过的去重）。
 * - 其它：展示后端 bk_error_msg；若消息为空或属于兜底层级文案，则替换为中性提示，
 *   绝不出现“异常 / 错误”字眼。
 * @param {Error} error
 * @param {Object} [vm] 组件实例（可选，缺省回退到 bindMagic 注入的实例）
 */
export function handleApiError(error, vm) {
  if (!error) return

  const code =
    error.bk_error_code ||
    (error.response && error.response.data && error.response.data.bk_error_code)
  if (code === NO_PERMISSION_CODE) {
    if (!error.handled) showNoPermission(error)
    return
  }

  const magic = getMagic(vm)
  if (!magic) return

  let msg =
    error.bk_error_msg ||
    (error.response && error.response.data && error.response.data.bk_error_msg) ||
    error.message ||
    ''

  // 兜底：禁止“异常 / 错误”等兜底层级文案出现在提示里
  if (!msg || /异常|错误|未知错误|业务处理失败|服务器内部错误/.test(msg)) {
    msg = '操作未成功，请稍后重试'
  }

  magic.$bkMessage({ theme: 'error', message: msg })
}
