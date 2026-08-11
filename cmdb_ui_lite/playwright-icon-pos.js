const { chromium } = require('playwright')
const EXEC = '/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome'
const BASE = 'http://localhost:3000'

;(async () => {
  const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()) })
  page.on('pageerror', e => errors.push('PAGEERR ' + e.message))

  await page.goto(`${BASE}/#/resource/host/1`, { waitUntil: 'networkidle' })
  // 切到主机属性 tab（默认即为 property）
  await page.waitForSelector('.property-item', { timeout: 15000 })
  await page.waitForTimeout(800)

  // 收集前 8 个 property-item 的布局信息（含左/右栏）
  const data = await page.evaluate(() => {
    const items = [...document.querySelectorAll('.property-item')]
    const out = []
    items.slice(0, 8).forEach((li, idx) => {
      const name = li.querySelector('.property-name')
      const outerVal = li.querySelector(':scope > .property-value') // host-details wrapper
      const editIcon = li.querySelector('.property-edit-button')
      const copyBox = li.querySelector('.copy-box')
      const innerVal = li.querySelector('.editable-property .property-value')
      const rect = el => el ? (({ left, top, width, height, right, bottom }) => ({ left, top, width, height, right, bottom }))(el.getBoundingClientRect()) : null
      out.push({
        idx,
        column: idx % 2 === 0 ? 'LEFT' : 'RIGHT',
        name: name ? name.textContent.trim() : null,
        itemRect: rect(li),
        outerValRect: rect(outerVal),
        innerValRect: rect(innerVal),
        editIconRect: rect(editIcon),
        copyBoxRect: rect(copyBox)
      })
    })
    return out
  })

  console.log('=== 主机详情页 属性项布局 (前8项) ===')
  for (const d of data) {
    const e = d.editIconRect, c = d.copyBoxRect, v = d.innerValRect, ov = d.outerValRect
    console.log(`#${d.idx} [${d.column}] ${d.name}`)
    console.log(`   item.left=${d.itemRect.left.toFixed(0)} item.right=${d.itemRect.right.toFixed(0)} item.width=${d.itemRect.width.toFixed(0)}`)
    if (ov) console.log(`   outerVal: left=${ov.left.toFixed(0)} right=${ov.right.toFixed(0)} width=${ov.width.toFixed(0)}`)
    if (v) console.log(`   innerVal: left=${v.left.toFixed(0)} top=${v.top.toFixed(0)} width=${v.width.toFixed(0)} height=${v.height.toFixed(0)} bottom=${v.bottom.toFixed(0)}`)
    if (e) console.log(`   editIcon: left=${e.left.toFixed(0)} top=${e.top.toFixed(0)} height=${e.height.toFixed(0)} right=${e.right.toFixed(0)}`)
    if (c) console.log(`   copyBox : left=${c.left.toFixed(0)} top=${c.top.toFixed(0)} height=${c.height.toFixed(0)} right=${c.right.toFixed(0)}`)
    // 图标相对 item 左缘的水平偏移 & 相对 item 顶缘的垂直偏移
    if (e) console.log(`   >>> editIcon.offsetX_from_item=${ (e.left - d.itemRect.left).toFixed(0) }  offsetY_from_item=${(e.top - d.itemRect.top).toFixed(0)}  centerY=${(e.top+e.height/2).toFixed(0)}`)
    if (c) console.log(`   >>> copyBox.offsetX_from_item=${ (c.left - d.itemRect.left).toFixed(0) }  offsetY_from_item=${(c.top - d.itemRect.top).toFixed(0)}  centerY=${(c.top+c.height/2).toFixed(0)}`)
    if (v && e) console.log(`   >>> editIcon.centerY - innerVal.centerY = ${((e.top+e.height/2)-(v.top+v.height/2)).toFixed(0)}`)
  }

  await page.screenshot({ path: '/tmp/host_icon_pos.png', fullPage: false })
  console.log('\n截图已保存 /tmp/host_icon_pos.png')
  if (errors.length) console.log('CONSOLE ERRORS:', errors.slice(0, 5))
  await browser.close()
})().catch(e => { console.error('FATAL', e); process.exit(1) })
