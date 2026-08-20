/* E2E：主机详情-所属拓扑，多点 node 链接去除，仅 module 一个链接（对齐原项目）
 *
 * 用 addInitScript 在每个页面加载前注入 token（localStorage + cookie），
 * 直跳详情页的 ensureAuth(/auth/me) 即可通过，不再整页刷新丢失登录态。
 * 进入 biz2 主机 11 详情（所属 module-141389 / api）。
 * 断言：
 *   1. 路径以整行文本渲染（如「蓝鲸平台 / 广州一区 / api」），不再有分段可点节点
 *   2. 多级 node（biz/set）不存在任何可点击链接元素
 *   3. 仅 module 一个分享图标 .topology-module-link，默认隐藏、悬停出现
 *   4. 点击 module 链接在新窗口打开业务拓扑，且 URL 含 node=module-141389（非 biz/set）
 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome'
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  // 先取一个有效 token（独立临时页），再用 addInitScript 让每个页面加载前都注入
  const tmp = await context.newPage();
  await tmp.goto('http://127.0.0.1:3000/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  const token = await tmp.evaluate(async () => {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bk_user_name: 'admin', bk_password: 'admin' })
    });
    return (await res.json()).data.bk_token;
  });
  await tmp.close();
  await context.addInitScript((t) => {
    localStorage.setItem('lite_bk_token', t);
    localStorage.setItem('lite_bk_user_name', 'admin');
    document.cookie = `lite_bk_token=${t}; path=/; max-age=3600`;
  }, token);

  const page = await context.newPage();
  const errors = [];
  const popups = [];
  page.on('pageerror', e => errors.push(`[pageerror] ${e.message}`));
  page.on('console', m => {
    if (m.type() === 'error' && !m.text().includes('Failed to load resource')) errors.push(`[console] ${m.text()}`);
  });
  context.on('page', p => popups.push(p));

  try {
    await page.goto('http://127.0.0.1:3000/#/business/2/index/host/11',
      { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForSelector('.topology-item', { timeout: 25000 });
    await page.waitForTimeout(1500);

    const state = await page.evaluate(() => {
      const label = [...document.querySelectorAll('.topology-label')].find(e => e.innerText.includes('所属拓扑'));
      const list = label && label.parentElement.querySelector('.topology-list');
      const items = list ? Array.from(list.querySelectorAll('.topology-item')) : [];
      const first = items[0];
      return {
        itemCount: items.length,
        pathText: first ? first.querySelector('.topology-path').innerText.trim() : null,
        legacySegNodes: list ? list.querySelectorAll('.topology-node').length : -1,
        moduleLinkCount: first ? first.querySelectorAll('.topology-module-link').length : -1,
        moduleLinkDefaultDisplay: first ? getComputedStyle(first.querySelector('.topology-module-link')).display : null,
        anyOtherLink: list ? list.querySelectorAll('a, [data-link]').length : -1
      };
    });

    await page.hover('.topology-item');
    await page.waitForTimeout(300);
    const hoverDisplay = await page.evaluate(() =>
      getComputedStyle(document.querySelector('.topology-module-link')).display);

    await page.click('.topology-module-link');
    await page.waitForTimeout(1500);
    const popupUrls = popups.map(p => p.url());

    console.log('=== 主机详情-所属拓扑 链接规范断言 ===');
    console.log(JSON.stringify(state, null, 2));
    console.log('悬停后 module 链接 display:', hoverDisplay);
    console.log('新开窗口 URL:', popupUrls);
    console.log('JS 错误数:', errors.length, errors.slice(0, 3));

    const pass =
      state.itemCount >= 1
      && / \/ /.test(state.pathText)
      && state.legacySegNodes === 0
      && state.moduleLinkCount === 1
      && state.moduleLinkDefaultDisplay === 'none'
      && hoverDisplay === 'inline-block'
      && state.anyOtherLink === 0
      && popups.length === 1
      && /node=module-141389/.test(popupUrls[0])
      && errors.length === 0;

    console.log(pass ? '\nHOST-TOPO-LINK PASS ✅' : '\nHOST-TOPO-LINK FAIL ❌');
    await browser.close();
    process.exit(pass ? 0 : 1);
  } catch (e) {
    const diag = await page.evaluate(() => ({
      url: location.href,
      infoTopo: !!document.querySelector('.info-topology'),
      bodyHead: document.body.innerText.replace(/\s+/g, ' ').slice(0, 140)
    })).catch(() => ({}));
    console.error('E2E 异常:', e.message, JSON.stringify(diag));
    await browser.close();
    process.exit(2);
  }
})();
