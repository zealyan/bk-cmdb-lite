const { chromium } = require('playwright')
const EXEC = '/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome'
const BASE = 'http://localhost:3000'

;(async () => {
  const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await page.goto(`${BASE}/#/resource/host/1`, { waitUntil: 'networkidle' })
  await page.waitForSelector('.property-item', { timeout: 15000 })
  await page.waitForTimeout(800)

  const rows = await page.evaluate(() => {
    const items = [...document.querySelectorAll('.property-item')]
    return items.map((li, idx) => {
      const name = li.querySelector('.property-name')?.textContent?.trim() || ''
      const val = li.querySelector('.editable-property .property-value')
      const edit = li.querySelector('.property-edit-button')
      const copy = li.querySelector('.property-copy')
      const rect = el => el ? el.getBoundingClientRect() : null
      return { idx, name, val: rect(val), edit: rect(edit), copy: rect(copy) }
    })
  })

  let pass = 0, fail = 0
  const failures = []

  for (const r of rows) {
    if (!r.edit) continue
    // 编辑图标应在值文本右侧 12px 处（允许 1px 测量误差）
    const editExpected = r.val ? r.val.right + 12 : null
    const editOk = editExpected !== null && Math.abs(r.edit.left - editExpected) <= 1
    // 复制图标应在编辑图标右侧 8px 处（copy 元素 margin-left:8px）
    let copyOk = true, copyExpected = null
    if (r.copy) {
      copyExpected = r.edit.right + 8
      copyOk = Math.abs(r.copy.left - copyExpected) <= 1
    }

    if (editOk && copyOk) {
      pass++
    } else {
      fail++
      failures.push({
        idx: r.idx,
        name: r.name,
        editLeft: r.edit.left,
        editExpected,
        copyLeft: r.copy?.left,
        copyExpected
      })
    }
  }

  console.log(`=== 图标位置不变量检查 ===`)
  console.log(`通过: ${pass} / 失败: ${fail}`)
  if (failures.length) {
    console.log('失败项:', failures.slice(0, 10))
  }
  console.log(fail === 0 ? '\n✅ 所有可编辑属性项的编辑/复制图标位置均符合上游规则' : '\n❌ 存在位置漂移')
  await browser.close()
  process.exit(fail === 0 ? 0 : 1)
})().catch(e => { console.error('FATAL', e); process.exit(1) })
