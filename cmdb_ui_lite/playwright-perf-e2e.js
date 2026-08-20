const { chromium } = require('playwright')

const EXEC = '/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome'
const BASE = 'http://localhost:3000'

function sleep (ms) { return new Promise(r => setTimeout(r, ms)) }

async function testList (page, model, totalExpected) {
  const errors = []
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message))
  page.on('console', m => { if (m.type() === 'error' && !/404/.test(m.text())) errors.push(m.text()) })

  // 用 URL 的 limit 参数驱动分页（组件读取 query.limit），选 500 验证分页只渲染当前页
  await page.goto(`${BASE}/#/resource/instance/${model}?limit=500`, { waitUntil: 'networkidle' })
  await page.waitForFunction(() => {
    const t = document.querySelector('.bk-table-body-wrapper tbody')
    return t && t.children.length > 0
  }, { timeout: 20000 }).catch(() => {})
  await sleep(800)

  const info = await page.evaluate(() => {
    const body = document.querySelector('.bk-table-body-wrapper')
    const tbody = body && body.querySelector('tbody')
    const rows = tbody ? tbody.children.length : 0
    const style = body ? getComputedStyle(body) : {}
    const firstRow = tbody && tbody.children[0]
    // bk-table 用 row-key 作 v-for 的 :key，DOM 上体现为稳定索引属性 data-table-row
    const hasRowKey = firstRow ? firstRow.hasAttribute('data-table-row') : false
    // 临时探针（loadModelData 赋值后写入）：验证列表数据已被 Object.freeze
    const probeFrozen = window.__TEST_LIST_FROZEN
    const probeLen = window.__TEST_LIST_LEN
    return {
      rows,
      bodyMaxHeight: style.maxHeight,
      hasMaxHeight: !!(style.maxHeight && style.maxHeight !== 'none'),
      hasRowKey,
      frozen: probeFrozen != null ? { arrFrozen: probeFrozen, len: probeLen } : null
    }
  })

  // 翻页取消验证：快速连续翻页，确认无未捕获错误
  const t0 = Date.now()
  for (let i = 0; i < 3; i++) {
    await page.evaluate(() => {
      const next = document.querySelector('.bk-pagination [class*="next"], .bk-pagination-next, a.next')
      if (next) next.click()
    }).catch(() => {})
    await sleep(250)
  }
  await sleep(500)
  const t1 = Date.now()

  // 触发卸载（离开列表）以验证 beforeDestroy 取消进行中的请求
  await page.goto(`${BASE}/#/resource/instance/bk_slb`, { waitUntil: 'networkidle' }).catch(() => {})
  await sleep(500)

  return {
    model,
    renderedRows: info.rows,
    totalExpected,
    hasMaxHeight: info.hasMaxHeight,
    bodyMaxHeight: info.bodyMaxHeight,
    hasRowKey: info.hasRowKey,
    frozen: info.frozen,
    pageSwitchMs: t1 - t0,
    errCount: errors.length,
    errors: errors.slice(0, 5)
  }
}

;(async () => {
  const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } })

  console.log('=== 主机列表（objId=host，总数 621，limit=500）===')
  const host = await testList(page, 'host', 621)
  console.log(JSON.stringify(host, null, 2))

  console.log('\n=== 实例列表（objId=bk_switch，总数 610，limit=500）===')
  const inst = await testList(page, 'bk_switch', 610)
  console.log(JSON.stringify(inst, null, 2))

  console.log('\n=== 断言 ===')
  const pass = (c, label) => console.log(`  ${c ? '✅' : '❌'} ${label}`)
  pass(host.renderedRows > 0 && host.renderedRows <= 500, `主机列表仅渲染当前页（${host.renderedRows} 行 / 总数 621，未全量渲染）`)
  pass(host.hasMaxHeight, `主机列表 max-height 固定表头+视口滚动（${host.bodyMaxHeight}）`)
  pass(host.hasRowKey, '主机列表 row-key 稳定 diff（DOM 回收/替换基础）')
  pass(host.frozen && host.frozen.arrFrozen, `主机列表数据已 Object.freeze（arrFrozen=${host.frozen && host.frozen.arrFrozen}, len=${host.frozen && host.frozen.len}）`)
  pass(host.errCount === 0, `主机列表翻页/卸载无控制台错误（请求取消正常，${host.errCount} 个错误）`)

  pass(inst.renderedRows > 0 && inst.renderedRows <= 500, `实例列表仅渲染当前页（${inst.renderedRows} 行 / 总数 610，未全量渲染）`)
  pass(inst.hasMaxHeight, `实例列表 max-height 固定表头+视口滚动（${inst.bodyMaxHeight}）`)
  pass(inst.hasRowKey, '实例列表 row-key 稳定 diff')
  pass(inst.frozen && inst.frozen.arrFrozen, `实例列表数据已 Object.freeze（arrFrozen=${inst.frozen && inst.frozen.arrFrozen}, len=${inst.frozen && inst.frozen.len}）`)
  pass(inst.errCount === 0, `实例列表翻页/卸载无控制台错误（请求取消正常，${inst.errCount} 个错误）`)

  await browser.close()
})().catch(e => { console.error('E2E 失败:', e); process.exit(1) })
