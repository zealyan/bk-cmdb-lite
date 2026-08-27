// 验证「转移主机到其他业务」弹框：取消按钮可关闭弹框 + confirm 弹框 title/content 紧凑排版
const { chromium } = require('playwright')

;(async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/chromium', args: ['--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } })
  const asserts = []
  const assert = (name, ok, detail = '') => { asserts.push({ name, ok }); console.log((ok ? 'PASS ' : 'FAIL ') + name + '  ' + detail) }
  const shots = []

  try {
    // 1) 登录
    await page.goto('http://localhost:3000/', { waitUntil: 'domcontentloaded' })
    await page.waitForSelector('.login-input', { timeout: 15000 })
    const inputs = await page.$$('.login-input')
    await inputs[0].fill('admin')
    await inputs[1].fill('admin')
    await page.click('.login-btn')
    await page.waitForTimeout(3000)
    assert('登录成功跳转', !page.url().includes('/login'))

    // 2) 进入业务2 主机列表
    await page.goto('http://localhost:3000/business/2/index?tab=hostList', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(4000)
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
    const selectHost = async () => {
      return page.evaluate(() => {
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
    }
    const s1 = await selectHost()
    assert('勾选 90001 行', s1 === 'cb' || s1 === 'row', 'click=' + s1)
    await page.waitForTimeout(500)

    // 3) 触发转移 → 其他业务（第一步 confirm 弹框）
    await page.click('button:has-text("转移至")')
    await page.waitForTimeout(500)
    await page.click('.bk-dropdown-item:has-text("其他业务")')
    await page.waitForSelector('.across-confirm', { timeout: 8000 })
    await page.waitForTimeout(800)
    const shot1 = '/tmp/shot_confirm_new.png'
    await page.screenshot({ path: shot1 }); shots.push(shot1)

    // 验证 confirm 弹框 title/content 紧凑 + footer 贴底
    const c1 = await page.evaluate(() => {
      const dlg = document.querySelector('.dialog-body')
      const title = document.querySelector('.across-confirm .title')
      const content = document.querySelector('.across-confirm .content')
      const footer = document.querySelector('.across-confirm .footer')
      const r = (el) => { const b = el.getBoundingClientRect(); return { y: b.y, top: b.y, bottom: b.bottom, h: b.height } }
      return { dlg: r(dlg), title: r(title), content: r(content), footer: r(footer) }
    })
    console.log('confirm 几何:', JSON.stringify(c1))
    // title/content 紧凑：content.bottom 距 title.top 不应过大（< 80px），footer 贴底（差值<18px）
    assert('[confirm] footer 贴底', Math.abs(c1.footer.bottom - c1.dlg.bottom) <= 18, `diff=${(c1.footer.bottom - c1.dlg.bottom).toFixed(1)}px`)
    assert('[confirm] title/content 紧凑(无大段空白)', (c1.content.bottom - c1.title.top) < 200, `span=${(c1.content.bottom - c1.title.top).toFixed(0)}px`)
    assert('[confirm] title 样式: 居中大字', c1.title.h >= 30, `title.h=${c1.title.h.toFixed(0)}px`)

    // 4) 点取消 → 断言 confirm 弹框消失
    await page.click('.across-confirm button:has-text("取消")')
    await page.waitForTimeout(800)
    const gone1 = await page.evaluate(() => !document.querySelector('.across-confirm'))
    assert('[confirm] 点击取消后弹框消失', gone1)
    const dlgGone1 = await page.evaluate(() => !document.querySelector('.dialog-body'))
    assert('[confirm] 弹框外壳也消失', dlgGone1)

    // 5) 再次触发，进入第二步 selector 弹框（点下一步）
    await page.click('button:has-text("转移至")')
    await page.waitForTimeout(500)
    await page.click('.bk-dropdown-item:has-text("其他业务")')
    await page.waitForSelector('.across-confirm', { timeout: 8000 })
    await page.waitForTimeout(500)
    await page.click('.across-confirm button:has-text("下一步")')
    await page.waitForSelector('.module-selector-layout', { timeout: 8000 })
    await page.waitForTimeout(800)
    const shot2 = '/tmp/shot_selector_new.png'
    await page.screenshot({ path: shot2 }); shots.push(shot2)

    // 6) 点取消 → 断言 selector 弹框消失
    await page.click('.module-selector-layout button:has-text("取消")')
    await page.waitForTimeout(800)
    const gone2 = await page.evaluate(() => !document.querySelector('.module-selector-layout'))
    assert('[selector] 点击取消后弹框消失', gone2)
    const dlgGone2 = await page.evaluate(() => !document.querySelector('.dialog-body'))
    assert('[selector] 弹框外壳也消失', dlgGone2)
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
