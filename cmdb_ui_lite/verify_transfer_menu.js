// 验证「转移至 → 其他业务」菜单项：非空闲机池节点下 disabled 不可点，空闲机池下可点弹出
const { chromium } = require('playwright')
const { execSync } = require('child_process')

const DB = '/workspace/bk-cmdb-lite/bk-cmdb-lite/cmdb_server_lite/cmdb_dev.db'
const bind = (hostId, bizId, moduleId, setId) => {
  execSync(`python3 -c "
import sqlite3
c=sqlite3.connect('${DB}'); cur=c.cursor()
cur.execute('DELETE FROM cc_ModuleHostConfig WHERE bk_host_id=${hostId}')
cur.execute('INSERT INTO cc_ModuleHostConfig (bk_biz_id,bk_host_id,bk_module_id,bk_set_id,bk_supplier_account) VALUES (${bizId},${hostId},${moduleId},${setId},\\'0\\')')
c.commit()
"`)
}

;(async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/chromium', args: ['--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } })
  const asserts = []
  const assert = (name, ok, detail = '') => { asserts.push({ name, ok }); console.log((ok ? 'PASS ' : 'FAIL ') + name + '  ' + detail) }
  const shots = []

  const login = async () => {
    await page.goto('http://localhost:3000/', { waitUntil: 'domcontentloaded' })
    await page.waitForSelector('.login-input', { timeout: 15000 })
    const inputs = await page.$$('.login-input')
    await inputs[0].fill('admin')
    await inputs[1].fill('admin')
    await page.click('.login-btn')
    await page.waitForTimeout(3000)
  }
  const enterNode = async (nodePath) => {
    await page.goto('http://localhost:3000/business/2/index?tab=hostList&node=' + nodePath, { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(3500)
  }
  const selectHost90001 = async () => {
    // 翻到第 2 页（90001 按 bk_host_id 排序在第 12 位左右）
    await page.evaluate(() => {
      const items = Array.from(document.querySelectorAll('.bk-pagination li, .bk-pagination .page-item, [class*="page"] li'))
      for (const li of items) {
        const t = (li.textContent || '').trim()
        if (t === '2' && !li.classList.contains('disabled') && !li.classList.contains('active')) { li.click(); return }
      }
      const next = document.querySelector('.bk-pagination-next, .bk-pagination .next')
      if (next) next.click()
    })
    await page.waitForTimeout(1800)
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
  const openMenu = async () => {
    await page.click('button:has-text("转移至")')
    await page.waitForTimeout(600)
  }
  const menuState = async () => {
    return page.evaluate(() => {
      const items = Array.from(document.querySelectorAll('.bk-dropdown-item'))
      const biz = items.find(li => /其他业务/.test(li.textContent || ''))
      const pool = items.find(li => /主机池/.test(li.textContent || ''))
      return {
        bizDisabled: biz ? biz.classList.contains('disabled') : null,
        poolDisabled: pool ? pool.classList.contains('disabled') : null
      }
    })
  }

  try {
    // ============ 场景1：非空闲机池节点 module-100，其他业务应 disabled 且不可点 ============
    bind(90001, 2, 100, 10)
    await login()
    console.log('\n===== 场景1: module-100(web, 非空闲机池) =====')
    await enterNode('module-100')
    const s1 = await selectHost90001()
    assert('勾选 90001(模块100)', s1 === 'cb' || s1 === 'row', 'click=' + s1)
    await openMenu()
    const st1 = await menuState()
    console.log('  菜单状态:', JSON.stringify(st1))
    assert('「其他业务」为 disabled 灰色', st1.bizDisabled === true, 'bizDisabled=' + st1.bizDisabled)
    assert('「主机池」为 disabled 灰色', st1.poolDisabled === true, 'poolDisabled=' + st1.poolDisabled)
    const shot1 = '/tmp/shot_menu_disabled.png'
    await page.screenshot({ path: shot1 }); shots.push(shot1)
    // 点击 disabled 的「其他业务」→ 不应弹出任何弹框
    await page.click('.bk-dropdown-item:has-text("其他业务")')
    await page.waitForTimeout(1200)
    const opened1 = await page.evaluate(() => !!document.querySelector('.across-confirm, .module-selector-layout'))
    assert('点击 disabled「其他业务」不弹框', !opened1, 'opened=' + opened1)
    // 关闭菜单
    await page.keyboard.press('Escape')
    await page.waitForTimeout(400)

    // ============ 场景2：空闲机池节点 module-4(空闲机)，其他业务应可点并弹出 ============
    bind(90001, 2, 4, 2)
    console.log('\n===== 场景2: module-4(空闲机, 空闲机池) =====')
    await enterNode('module-4')
    const s2 = await selectHost90001()
    assert('勾选 90001(空闲机模块)', s2 === 'cb' || s2 === 'row', 'click=' + s2)
    await openMenu()
    const st2 = await menuState()
    console.log('  菜单状态:', JSON.stringify(st2))
    assert('「其他业务」非 disabled', st2.bizDisabled === false, 'bizDisabled=' + st2.bizDisabled)
    assert('「主机池」非 disabled', st2.poolDisabled === false, 'poolDisabled=' + st2.poolDisabled)
    const shot2 = '/tmp/shot_menu_enabled.png'
    await page.screenshot({ path: shot2 }); shots.push(shot2)
    // 点击可用的「其他业务」→ 应弹出 confirm 弹框
    await page.click('.bk-dropdown-item:has-text("其他业务")')
    await page.waitForSelector('.across-confirm', { timeout: 6000 })
    const shot3 = '/tmp/shot_across_from_idle.png'
    await page.screenshot({ path: shot3 }); shots.push(shot3)
    assert('点击可用「其他业务」弹出 confirm 弹框', true)
    // 取消关闭
    await page.click('.across-confirm button:has-text("取消")')
    await page.waitForTimeout(600)
    const closed = await page.evaluate(() => !document.querySelector('.across-confirm'))
    assert('取消后弹框关闭', closed)
  } catch (e) {
    console.log('ERROR', e.message)
    assert('脚本执行无异常', false, e.message)
  } finally {
    // 恢复 90001 到业务2/模块100
    try { bind(90001, 2, 100, 10); console.log('\n[cleanup] 90001 已恢复至业务2/模块100') } catch (e) { console.log('[cleanup] 恢复失败', e.message) }
    const pass = asserts.filter(a => a.ok).length, fail = asserts.filter(a => !a.ok).length
    console.log(`\n==== 结果 PASS=${pass} FAIL=${fail} ====`)
    console.log('截图:', shots.join(', '))
    await browser.close()
    process.exit(fail ? 1 : 0)
  }
})()
