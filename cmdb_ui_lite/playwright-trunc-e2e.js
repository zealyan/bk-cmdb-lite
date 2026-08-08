// e2e：验证详情页属性值「长文本截断(...) + 悬停 tooltip 全文」
// 覆盖：主机详情页、实例详情页；并验证实例详情页截断不限于属性类型（longchar 与 singlechar 均生效）
// 脚本会先把三个字段写入长值，测试完成后自动恢复。
const { chromium } = require('playwright')

const EXEC = '/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome'
const BASE = 'http://localhost:3000'
const API = 'http://localhost:5000/api/v1'

const LONGCHAR_SEG = ('这是一段用于验证【属性值长文本截断 + 悬停 tips】的 longchar 文本；'
  + '当属性值超过值区宽度时应以省略号(...)截短，并将鼠标悬停在属性值上以 tooltip 展示完整内容。'
  + 'bk-cmdb 原项目通过 cmdb-property-value 的 is-show-overflow-tips 与 v-bk-overflow-tips 指令实现该能力，'
  + '本 lite 版在 editable-property 组件中复用同一指令，且对所有属性类型统一生效。')

function repeatTo (seg, n) {
  let s = ''
  while (s.length < n) s += seg
  return s.slice(0, n)
}

async function fetchText (model, id, field) {
  const r = await fetch(`${API}/models/${model}/instances/${id}`)
  const d = await r.json()
  const inst = (d.data && d.data.instance) || {}
  return String(inst[field] != null ? inst[field] : '')
}

async function updateText (model, id, data) {
  const r = await fetch(`${API}/models/${model}/instances/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data })
  })
  const d = await r.json()
  if (!d.result && d.bk_error_msg) throw new Error(`update ${model}/${id} failed: ${d.bk_error_msg}`)
}

let GROUND = { host_comment: '', slb_desc: '', slb_lb_name: '' }
let ORIGIN = { host_comment: '', slb_desc: '', slb_lb_name: '' }

async function check (page, { name, url, rowSel, label, fullText, fullLen }) {
  const res = { name, url, label, pass: true, details: [] }
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 })
    const row = page.locator(rowSel, { hasText: label }).first()
    const valueEl = row.locator('.editable-property .property-value').first()
    await valueEl.waitFor({ state: 'visible', timeout: 20000 })
    await page.waitForTimeout(400)

    const info = await valueEl.evaluate(el => {
      const cs = getComputedStyle(el)
      return {
        lineClamp: cs.webkitLineClamp,
        textOverflow: cs.textOverflow,
        overflow: cs.overflow,
        display: cs.display,
        scrollH: el.scrollHeight,
        clientH: el.clientHeight,
        textLen: el.textContent.length
      }
    })
    res.details.push(`lineClamp=${info.lineClamp} textOverflow=${info.textOverflow} overflow=${info.overflow} display=${info.display}`)
    res.details.push(`scrollH=${info.scrollH} clientH=${info.clientH} 数据textLen=${info.textLen}`)

    const implOk = info.lineClamp === '2' && info.textOverflow === 'ellipsis' && info.overflow === 'hidden'
    const truncated = info.scrollH > info.clientH + 2
    const dataFull = info.textLen >= fullLen - 50

    await valueEl.hover()
    let tipText = ''
    try {
      const handle = await valueEl.elementHandle()
      await page.waitForFunction(
        arg => arg && arg._tippy && arg._tippy.state && arg._tippy.state.isVisible,
        handle,
        { timeout: 8000 }
      )
      tipText = await valueEl.evaluate(el => {
        const c = el._tippy && el._tippy.popper && el._tippy.popper.querySelector('.tippy-content')
        return c ? c.textContent : ''
      })
    } catch (e) {
      tipText = ''
    }
    res.details.push(`tooltip文本长度=${tipText.length} (期望≈${fullLen}) | 前缀匹配=${tipText.slice(0, 25) === fullText.slice(0, 25)}`)
    const tipOk = tipText.length >= fullLen - 50 && tipText.slice(0, 25) === fullText.slice(0, 25)

    res.pass = implOk && truncated && dataFull && tipOk
    res.metrics = { implOk, truncated, dataFull, tipOk, scrollH: info.scrollH, clientH: info.clientH, tipLen: tipText.length, fullLen }
    await page.screenshot({ path: `/tmp/trunc_${name.replace(/[^a-z0-9]/gi, '_')}.png`, fullPage: false })
  } catch (err) {
    res.pass = false
    res.error = String(err && err.message ? err.message : err)
  }
  return res
}

async function setup () {
  // 备份原值
  ORIGIN.host_comment = await fetchText('host', 1, 'bk_comment')
  ORIGIN.slb_desc = await fetchText('bk_slb', 10000, 'description')
  ORIGIN.slb_lb_name = await fetchText('bk_slb', 10000, 'bk_lb_name')

  // 写入长值
  await updateText('host', 1, { bk_comment: repeatTo(LONGCHAR_SEG, 2000) })
  await updateText('bk_slb', 10000, {
    description: repeatTo(LONGCHAR_SEG, 2000),
    bk_lb_name: repeatTo(LONGCHAR_SEG, 1500)
  })

  // 以真实落库值为基准
  GROUND.host_comment = await fetchText('host', 1, 'bk_comment')
  GROUND.slb_desc = await fetchText('bk_slb', 10000, 'description')
  GROUND.slb_lb_name = await fetchText('bk_slb', 10000, 'bk_lb_name')
}

async function teardown () {
  // 恢复
  await updateText('host', 1, { bk_comment: ORIGIN.host_comment })
  await updateText('bk_slb', 10000, {
    description: ORIGIN.slb_desc,
    bk_lb_name: ORIGIN.slb_lb_name
  })
}

;(async () => {
  let browser, ctx, page
  try {
    await setup()
    console.log(`基准长度: SLB_DESC=${GROUND.slb_desc.length} SLB_LBNAME=${GROUND.slb_lb_name.length} HOST_COMMENT=${GROUND.host_comment.length}`)

    browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] })
    ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } })
    page = await ctx.newPage()
    const results = []

    // 主机详情页（longchar 类型：bk_comment / 备注）
    results.push(await check(page, {
      name: 'host-longchar',
      url: `${BASE}/#/resource/host/1`,
      rowSel: '.property-item',
      label: '备注',
      fullText: GROUND.host_comment,
      fullLen: GROUND.host_comment.length
    }))

    // 实例详情页（longchar 类型：description / 描述）
    results.push(await check(page, {
      name: 'instance-longchar',
      url: `${BASE}/#/resource/instance/bk_slb/10000`,
      rowSel: '.info-item',
      label: '描述',
      fullText: GROUND.slb_desc,
      fullLen: GROUND.slb_desc.length
    }))

    // 实例详情页（singlechar 类型：bk_lb_name / SLB名称）—— 证明"不限于属性类型"
    results.push(await check(page, {
      name: 'instance-singlechar',
      url: `${BASE}/#/resource/instance/bk_slb/10000`,
      rowSel: '.info-item',
      label: 'SLB名称',
      fullText: GROUND.slb_lb_name,
      fullLen: GROUND.slb_lb_name.length
    }))

    await browser.close()
    browser = null

    let allPass = true
    for (const r of results) {
      allPass = allPass && r.pass
      console.log(`\n===== [${r.pass ? 'PASS' : 'FAIL'}] ${r.name} | label=${r.label} =====`)
      console.log(`  url: ${r.url}`)
      r.details.forEach(d => console.log('  - ' + d))
      if (r.error) console.log('  ERROR: ' + r.error)
    }
    console.log(`\n===== 总结果: ${allPass ? 'ALL PASS' : 'HAS FAIL'} =====`)
    console.log(JSON.stringify(results.map(r => ({ name: r.name, pass: r.pass, metrics: r.metrics || null, error: r.error || null })), null, 2))
  } catch (err) {
    console.error('E2E 异常:', err)
  } finally {
    try { await teardown() } catch (e) { console.error('teardown 失败:', e) }
    if (browser) await browser.close().catch(() => {})
  }
})()
