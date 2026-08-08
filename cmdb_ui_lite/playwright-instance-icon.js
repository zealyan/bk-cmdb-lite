const { chromium } = require('playwright')
const EXEC = '/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome'
const BASE = 'http://localhost:3000'

;(async () => {
  const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await page.goto(`${BASE}/#/resource/instance/bk_slb/10000`, { waitUntil: 'networkidle' })
  await page.waitForSelector('.info-item', { timeout: 15000 })
  await page.waitForTimeout(800)

  // hover 第一个非 id 属性项
  const el = await page.$('.info-item:nth-child(2) .editable-property')
  if (el) {
    await el.hover()
    await page.waitForTimeout(400)
  }
  await page.screenshot({ path: '/tmp/instance_icon_hover.png', fullPage: false })
  console.log('截图已保存 /tmp/instance_icon_hover.png')
  await browser.close()
})().catch(e => { console.error('FATAL', e); process.exit(1) })
