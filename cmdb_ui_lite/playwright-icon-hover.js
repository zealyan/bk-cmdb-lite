const { chromium } = require('playwright')
const EXEC = '/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome'
const BASE = 'http://localhost:3000'

;(async () => {
  const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await page.goto(`${BASE}/#/resource/host/1`, { waitUntil: 'networkidle' })
  await page.waitForSelector('.property-item', { timeout: 15000 })
  await page.waitForTimeout(800)

  // 依次 hover 左栏 #0 内网IP、右栏 #5 主要维护人、左栏 #6 备份维护人、右栏 #7 固资编号
  const targets = [0, 1, 5, 6, 7]
  for (const idx of targets) {
    const sel = `.property-item:nth-child(${idx + 1}) .editable-property`
    const el = await page.$(sel)
    if (el) {
      await el.hover()
      await page.waitForTimeout(400)
      await page.screenshot({ path: `/tmp/host_hover_${idx}.png`, fullPage: false })
    }
  }

  console.log('截图已保存：/tmp/host_hover_*.png')
  await browser.close()
})().catch(e => { console.error('FATAL', e); process.exit(1) })
