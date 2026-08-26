// 验证登录请求过程态：显示 bk-loading 遮罩（含提示文字），请求返回后消失
const { chromium } = require('playwright')

;(async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/chromium', args: ['--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } })
  const asserts = []
  const assert = (name, ok, detail = '') => { asserts.push({ name, ok }); console.log((ok ? 'PASS ' : 'FAIL ') + name + '  ' + detail) }
  const shots = []
  let loginResponseStarted = false

  try {
    // 拦截登录接口，模拟 2.5s 网络延迟（返回结果前的过程态）
    await page.route('**/api/v1/auth/login', async (route) => {
      loginResponseStarted = true
      await new Promise(r => setTimeout(r, 2500))
      await route.continue()
    })

    await page.goto('http://localhost:3000/', { waitUntil: 'domcontentloaded' })
    await page.waitForSelector('.login-input', { timeout: 15000 })
    const inputs = await page.$$('.login-input')
    await inputs[0].fill('admin')
    await inputs[1].fill('admin')

    // 点击登录（loading 应立即出现）
    await page.click('.login-btn')
    await page.waitForTimeout(500)

    // 断言 1：请求已发出（过程态）
    assert('登录请求已发出', loginResponseStarted)

    // 断言 2：bk-loading 遮罩出现
    const loadingBox = await page.$('.bk-loading')
    assert('bk-loading 遮罩出现', !!loadingBox)
    // 断言 3：遮罩上显示提示文字
    const titleText = await page.evaluate(() => {
      const el = document.querySelector('.bk-loading-title')
      return el ? el.textContent.trim() : ''
    })
    assert('loading 提示文字"登录中…"', titleText === '登录中…', 'text=' + JSON.stringify(titleText))
    // 断言 4：遮罩覆盖整页（在登录按钮之上，z 序最高层）
    const zCheck = await page.evaluate(() => {
      const mask = document.querySelector('.bk-loading')
      const btn = document.querySelector('.login-btn')
      if (!mask || !btn) return null
      const mr = mask.getBoundingClientRect(), br = btn.getBoundingClientRect()
      return {
        maskCoversViewport: mr.width >= window.innerWidth * 0.9 && mr.height >= window.innerHeight * 0.9,
        maskAboveButton: mr.bottom >= br.bottom && mr.top <= br.top
      }
    })
    assert('遮罩覆盖整页且在按钮之上', zCheck && zCheck.maskCoversViewport && zCheck.maskAboveButton, JSON.stringify(zCheck))
    const shot = '/tmp/shot_login_loading.png'
    await page.screenshot({ path: shot }); shots.push(shot)

    // 等待请求返回并跳转
    await page.waitForTimeout(3200)
    const urlAfter = page.url()
    assert('登录成功后跳转（不在 /login）', !urlAfter.includes('/login'), 'url=' + urlAfter)
    // 断言 5：登录页(含其 loading 遮罩)已卸载
    const loginGone = await page.evaluate(() => !document.querySelector('.login-page'))
    assert('登录完成后登录页(含loading)已卸载', loginGone)
    // 断言 6：登录 loading 专属提示文案不再残留（目标页自身 loading 不算）
    await page.waitForTimeout(1500)
    const loginTitleGone = await page.evaluate(() => {
      return !Array.from(document.querySelectorAll('.bk-loading-title'))
        .some(el => (el.textContent || '').includes('登录中'))
    })
    assert('登录 loading 提示文字不再残留', loginTitleGone)
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
