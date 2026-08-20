const { chromium } = require('playwright')

const CHROME = '/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome'
const BASE = 'http://localhost:3000'
const TARGET = `${BASE}/#/resource/host/1`

;(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: CHROME,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  })
  const page = await browser.newPage({ viewport: { width: 1680, height: 1000 } })
  const errors = []
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()) })
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message))

  await page.goto(TARGET, { waitUntil: 'networkidle' })
  await page.waitForSelector('.property-item', { timeout: 20000 })
  await page.waitForTimeout(1200)

  const measure = await page.evaluate(() => {
    const items = Array.from(document.querySelectorAll('.property-item'))
    const rows = []
    items.forEach((item, i) => {
      const name = item.querySelector('.property-name')
      const valueText = item.querySelector('.property-value .editable-property .property-value')
        || item.querySelector('.property-value .property-value')
        || item.querySelector('.property-value')
      if (!name || !valueText) return
      const nb = name.getBoundingClientRect()
      const vb = valueText.getBoundingClientRect()
      const nameCenter = nb.top + nb.height / 2
      const valueCenter = vb.top + vb.height / 2
      rows.push({
        idx: i,
        name: name.textContent.trim().slice(0, 12),
        nameCenter: +nameCenter.toFixed(1),
        valueCenter: +valueCenter.toFixed(1),
        diff: +(valueCenter - nameCenter).toFixed(1),
        itemW: +item.getBoundingClientRect().width.toFixed(0),
        nameW: +nb.width.toFixed(0),
        valueW: +vb.width.toFixed(0)
      })
    })

    // 栏位统计：按 top 分组后，忽略仅含 1 个的最后一行（奇数属性时正常）
    const byTop = {}
    items.forEach(it => {
      const t = Math.round(it.getBoundingClientRect().top)
      byTop[t] = (byTop[t] || 0) + 1
    })
    const colCounts = Object.values(byTop)
    const fullRowCols = colCounts.filter(c => c >= 2)
    const isTwoCol = fullRowCols.length > 0 && fullRowCols.every(c => c === 2)

    const listW = document.querySelector('.property-list')?.getBoundingClientRect().width || 0
    const propertyW = document.querySelector('.property')?.getBoundingClientRect().width || 0
    const avgItemW = rows.reduce((s, r) => s + r.itemW, 0) / (rows.length || 1)
    return {
      rows,
      colCounts,
      isTwoCol,
      listW: +listW.toFixed(0),
      propertyW: +propertyW.toFixed(0),
      avgItemW: +avgItemW.toFixed(0)
    }
  })

  const maxAbsDiff = measure.rows.reduce((m, r) => Math.max(m, Math.abs(r.diff)), 0)
  const badRows = measure.rows.filter(r => Math.abs(r.diff) > 3)
  const maxItemW = measure.rows.reduce((m, r) => Math.max(m, r.itemW), 0)

  await page.screenshot({ path: '/workspace/bk-cmdb-lite/cmdb_ui_lite/pw-align.png', fullPage: false })

  console.log('=== 栏位 ===')
  console.log('.property 容器宽度:', measure.propertyW, 'px')
  console.log('.property-list 宽度:', measure.listW, 'px')
  console.log('每行 item 数:', measure.colCounts)
  console.log('是否稳定两栏:', measure.isTwoCol ? '两栏 ✓' : '非两栏 ✗')
  console.log('')
  console.log('=== item 宽度 ===')
  console.log('平均 item 宽度:', measure.avgItemW, 'px')
  console.log('最大 item 宽度:', maxItemW, 'px', maxItemW <= 620 ? '(适中 ✓)' : '(过宽 ✗)')
  console.log('')
  console.log('=== name/value 垂直中心对齐 (diff = value中心 - name中心, 单位 px) ===')
  console.log('采样前 12 行:')
  measure.rows.slice(0, 12).forEach(r => {
    console.log(`  #${r.idx} ${r.name.padEnd(12)} diff=${r.diff.toString().padStart(3)} itemW=${r.itemW}`)
  })
  console.log('')
  console.log('最大绝对偏差:', maxAbsDiff, 'px', maxAbsDiff <= 3 ? '(对齐 ✓)' : '(错位 ✗)')
  console.log('错位行数(>3px):', badRows.length)
  console.log('总属性行:', measure.rows.length)
  console.log('')
  console.log('=== 控制台错误 ===')
  console.log(errors.length ? errors.slice(0, 8).join('\n') : '(无)')

  await browser.close()
})().catch(e => { console.error('TEST ERROR:', e); process.exit(1) })
