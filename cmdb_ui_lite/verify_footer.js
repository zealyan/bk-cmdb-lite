// 验证「转移主机到其他业务」两步骤弹框的 footer 是否贴底、取消按钮是否可见可用
const { chromium } = require('playwright')

;(async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/chromium', args: ['--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } })
  const shots = []
  const asserts = []
  const assert = (name, ok, detail = '') => { asserts.push({ name, ok, detail }); console.log((ok ? 'PASS ' : 'FAIL ') + name + '  ' + detail) }

  try {
    // 1) 登录 admin/admin
    await page.goto('http://localhost:3000/', { waitUntil: 'domcontentloaded' })
    await page.waitForSelector('.login-input', { timeout: 15000 })
    const inputs = await page.$$('.login-input')
    await inputs[0].fill('admin')
    await inputs[1].fill('admin')
    await page.click('.login-btn')
    await page.waitForTimeout(3000)
    assert('登录成功跳转', !page.url().includes('/login'), 'url=' + page.url())

    // 2) 进入业务2 主机列表
    await page.goto('http://localhost:3000/business/2/index?tab=hostList', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(4000)

    // 90001 在第 12 位（每页10条）→ 翻到第 2 页
    await page.evaluate(() => {
      const items = Array.from(document.querySelectorAll('.bk-pagination li, .bk-pagination .page-item, [class*="page"] li'))
      for (const li of items) {
        const t = (li.textContent || '').trim()
        if (t === '2' && !li.classList.contains('disabled') && !li.classList.contains('active')) { li.click(); return }
      }
      const next = document.querySelector('.bk-pagination-next, .bk-pagination .next')
      if (next) next.click()
    })
    await page.waitForTimeout(2000)

    // 勾选 90001 行
    const clicked = await page.evaluate(() => {
      const all = Array.from(document.querySelectorAll('*'))
      const hit = all.find(el => el.children.length === 0 && /90001/.test(el.textContent || ''))
      if (!hit) return 'no-host'
      let row = hit
      while (row && row.parentElement) {
        if (row.tagName === 'TR' || /row|table-row/i.test(row.className || '')) break
        row = row.parentElement
      }
      const cb = row.querySelector('.bk-checkbox') || row.querySelector('input[type=checkbox]')
      if (cb) { cb.click(); return 'cb' }
      row.click(); return 'row'
    })
    assert('找到并勾选 90001 行', clicked === 'cb' || clicked === 'row', 'click=' + clicked)
    await page.waitForTimeout(500)

    // 3) 转移至 → 其他业务
    await page.click('button:has-text("转移至")')
    await page.waitForTimeout(500)
    await page.click('.bk-dropdown-item:has-text("其他业务")')
    await page.waitForTimeout(1500)

    // 4) 第一步 confirm 弹框
    await page.waitForSelector('.across-confirm', { timeout: 8000 })
    await page.waitForTimeout(600)
    const confirm = await page.evaluate(() => {
      const dlg = document.querySelector('.dialog-body')
      const footer = document.querySelector('.across-confirm .footer')
      const btn = Array.from(document.querySelectorAll('.across-confirm button')).find(b => /取消/.test(b.textContent))
      const r = (el) => { const b = el.getBoundingClientRect(); return { x: b.x, y: b.y, w: b.width, h: b.height, bottom: b.bottom, right: b.right } }
      return { dlg: r(dlg), footer: footer ? r(footer) : null, cancel: btn ? r(btn) : null }
    })
    const shot1 = '/tmp/shot_confirm.png'
    await page.screenshot({ path: shot1 }); shots.push(shot1)
    console.log('confirm 几何:', JSON.stringify(confirm))
    if (confirm.cancel && confirm.dlg) {
      const inDlg = confirm.cancel.y >= confirm.dlg.y - 1 && confirm.cancel.bottom <= confirm.dlg.bottom + 1
      assert('[确认弹框] 取消按钮未被裁切(在弹框内)', inDlg, `btn.bottom=${confirm.cancel.bottom.toFixed(0)} dlg.bottom=${confirm.dlg.bottom.toFixed(0)}`)
      const stick = Math.abs(confirm.cancel.bottom - confirm.dlg.bottom) <= 18
      assert('[确认弹框] 取消按钮贴底', stick, `差值=${Math.abs(confirm.cancel.bottom - confirm.dlg.bottom).toFixed(1)}px`)
      const visible = confirm.cancel.h > 0 && confirm.cancel.w > 0 && confirm.cancel.y > 0
      assert('[确认弹框] 取消按钮可见可点', visible, `w=${confirm.cancel.w.toFixed(0)} h=${confirm.cancel.h.toFixed(0)}`)
    } else {
      assert('[确认弹框] 定位到取消按钮', false, 'cancel=' + JSON.stringify(confirm.cancel) + ' dlg=' + JSON.stringify(confirm.dlg))
    }

    // 5) 下一步 → 第二步 selector 弹框
    await page.click('button:has-text("下一步")')
    await page.waitForSelector('.module-selector-layout', { timeout: 8000 })
    await page.waitForTimeout(800)
    const selector = await page.evaluate(() => {
      const dlg = document.querySelector('.dialog-body')
      const footer = document.querySelector('.module-selector-layout .layout-footer')
      const btn = Array.from(document.querySelectorAll('.module-selector-layout button')).find(b => /取消/.test(b.textContent))
      const r = (el) => { const b = el.getBoundingClientRect(); return { x: b.x, y: b.y, w: b.width, h: b.height, bottom: b.bottom, right: b.right } }
      return { dlg: r(dlg), footer: footer ? r(footer) : null, cancel: btn ? r(btn) : null }
    })
    const shot2 = '/tmp/shot_selector.png'
    await page.screenshot({ path: shot2 }); shots.push(shot2)
    console.log('selector 几何:', JSON.stringify(selector))
    if (selector.cancel && selector.dlg) {
      const inDlg = selector.cancel.y >= selector.dlg.y - 1 && selector.cancel.bottom <= selector.dlg.bottom + 1
      assert('[选择弹框] 取消按钮未被裁切(在弹框内)', inDlg, `btn.bottom=${selector.cancel.bottom.toFixed(0)} dlg.bottom=${selector.dlg.bottom.toFixed(0)}`)
      const stick = Math.abs(selector.cancel.bottom - selector.dlg.bottom) <= 18
      assert('[选择弹框] 取消按钮贴底', stick, `差值=${Math.abs(selector.cancel.bottom - selector.dlg.bottom).toFixed(1)}px`)
      const visible = selector.cancel.h > 0 && selector.cancel.w > 0 && selector.cancel.y > 0
      assert('[选择弹框] 取消按钮可见可点', visible, `w=${selector.cancel.w.toFixed(0)} h=${selector.cancel.h.toFixed(0)}`)
    } else {
      assert('[选择弹框] 定位到取消按钮', false, 'cancel=' + JSON.stringify(selector.cancel) + ' dlg=' + JSON.stringify(selector.dlg))
    }
  } catch (e) {
    console.log('ERROR', e.message)
    assert('脚本执行无异常', false, e.message)
  } finally {
    const pass = asserts.filter(a => a.ok).length, fail = asserts.filter(a => !a.ok).length
    console.log(`\n==== 结果 PASS=${pass} FAIL=${fail} ====`)
    console.log('截图:', shots.join(', '))
    await browser.close()
    process.exit(fail ? 1 : 0)
  }
})()
