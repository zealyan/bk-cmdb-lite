/* E2E：业务拓扑 keyword 的 URL 构造 + 路由同步 + 刷新后定位
 *
 * 对齐原项目 topology-tree.vue 中 keyword 经 RouterQuery 的双向同步：
 *   - 打开带 ?keyword=api 的 URL：搜索框回填 'api'（从 URL 恢复 / 路由同步）
 *   - 刷新页面后：搜索框仍 'api' 且树仍按 api 过滤（刷新后定位保持）
 *   - 搜索框输入 'biz'：URL query 出现 keyword=biz（URL 构造）
 */
const { chromium } = require('playwright');

const BASE = process.env.BASE || 'http://127.0.0.1:3100';

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome'
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  // 先取有效 token，再用 addInitScript 让每个页面加载前注入，避免整页刷新丢登录态
  const tmp = await context.newPage();
  await tmp.goto(`${BASE}/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
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
  page.on('pageerror', e => errors.push(`[pageerror] ${e.message}`));
  page.on('console', m => {
    if (m.type() === 'error' && !m.text().includes('Failed to load resource')) errors.push(`[console] ${m.text()}`);
  });

  const readState = async () => page.evaluate(() => {
    const input = document.querySelector('.tree-search input');
    // 注意：业务拓扑是 hash 路由，query 在 location.hash 里（#/business/2/index?keyword=api），
    // 不在 location.search。需从 hash 中解析。
    const hash = location.hash || '';
    const q = new URLSearchParams(hash.split('?')[1] || '');
    const treeEl = document.querySelector('.topology-tree');
    const treeText = (treeEl ? treeEl.innerText : '').replace(/\s+/g, ' ').trim();
    return {
      keyword: input ? input.value : null,
      urlKeyword: q.get('keyword'),
      treeHasApi: /api/i.test(treeText),
      treeSnippet: treeText.slice(0, 100)
    };
  });

  try {
    // 1) 打开带 keyword 的 URL（模拟从详情/其他页跳入，或刷新）
    await page.goto(`${BASE}/#/business/2/index?keyword=api`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('.tree-search input', { timeout: 25000 });
    await page.waitForTimeout(3500);
    const s1 = await readState();

    // 2) 刷新页面（核心：刷新后定位）
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('.tree-search input', { timeout: 25000 });
    await page.waitForTimeout(3500);
    const s2 = await readState();

    // 3) 构造验证：搜索框输入 -> URL 出现 keyword
    await page.fill('.tree-search input', 'biz');
    await page.waitForTimeout(900);
    const urlAfterInput = page.url();
    const s3 = await readState();

    console.log('=== keyword URL 构造 + 路由同步 + 刷新定位 ===');
    console.log('打开(带keyword=api):', JSON.stringify(s1));
    console.log('刷新后:', JSON.stringify(s2));
    console.log('输入biz后 URL:', urlAfterInput);
    console.log('输入后状态:', JSON.stringify(s3));
    console.log('JS 错误数:', errors.length, errors.slice(0, 3));

    const pass =
      s1.keyword === 'api' &&
      s2.keyword === 'api' &&              // 刷新后定位：搜索框回填保持
      s2.urlKeyword === 'api' &&
      s2.treeHasApi &&                     // 刷新后树仍按 keyword 过滤显示匹配节点
      /keyword=biz/.test(urlAfterInput) && // URL 构造：输入写入 query
      s3.keyword === 'biz' &&
      errors.length === 0;

    console.log(pass ? '\nKEYWORD-URL-SYNC PASS ✅' : '\nKEYWORD-URL-SYNC FAIL ❌');
    await browser.close();
    process.exit(pass ? 0 : 1);
  } catch (e) {
    const diag = await page.evaluate(() => ({ url: location.href, bodyHead: document.body.innerText.replace(/\s+/g, ' ').slice(0, 160) })).catch(() => ({}));
    console.error('E2E 异常:', e.message, JSON.stringify(diag));
    await browser.close();
    process.exit(2);
  }
})();
