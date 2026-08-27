/* 冒烟测试：转移到业务模块弹框（R6/R7 修复验证；R12 后全量加载）
 * 1. 打开 biz2 主机列表
 * 2. 勾选一台主机
 * 3. 点击「转移至」→「业务模块」
 * 4. 断言：无 TypeError；业务树全量渲染出节点（无 /topo/instance/children|path 懒加载请求）；默认模块直接命中勾选
 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome'
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  const errors = [];
  const requests = [];
  page.on('console', (msg) => {
    // 忽略静态资源 404（favicon 等），只关注 JS 运行时错误
    if (msg.type() === 'error' && !msg.text().includes('Failed to load resource')) {
      errors.push(`[console.error] ${msg.text()}`);
    }
  });
  page.on('pageerror', (err) => errors.push(`[pageerror] ${err.message}`));
  page.on('request', (req) => {
    const url = req.url();
    if (url.includes('/topo/instance/children') || url.includes('/topo/instance/path')) {
      requests.push(`${req.method()} ${url.split('/api/v1')[1]}`);
    }
  });

  try {
    // 前置登录：服务已开启强制登录（SKIP_LOGIN=false），先用 API 拿 token
    // 并注入 localStorage/cookie，再进入业务页（测试自足，不依赖人工登录态）。
    const loginRes = await fetch('http://127.0.0.1:5000/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bk_user_name: 'admin', bk_password: 'admin' })
    });
    const loginData = await loginRes.json();
    if (!loginData.result || !loginData.data || !loginData.data.bk_token) {
      throw new Error('登录失败: ' + JSON.stringify(loginData).slice(0, 200));
    }
    await page.addInitScript((t) => {
      localStorage.setItem('lite_bk_token', t);
      localStorage.setItem('lite_bk_user_name', 'admin');
      document.cookie = `lite_bk_token=${t}; path=/`;
    }, loginData.data.bk_token);

    await page.goto('http://127.0.0.1:3000/business/2/index', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1500);

    // 勾选第一台主机（bk-table 复选框为 label.bk-form-checkbox > span.bk-checkbox）
    const checkbox = page.locator('.host-table tbody tr .bk-form-checkbox span.bk-checkbox').first();
    await checkbox.click({ timeout: 10000, force: true });
    await page.waitForTimeout(400);

    // 打开「转移至」下拉，点「业务模块」
    await page.locator('text=转移至').first().click({ timeout: 10000 });
    await page.waitForTimeout(300);
    await page.locator('.bk-dropdown-item', { hasText: '业务模块' }).click({ timeout: 10000 });
    await page.waitForTimeout(4000);

    // 断言：弹框中业务树渲染出节点（biz 根 + 展开后的 set）
    const treeText = await page.locator('.module-selector-layout').innerText().catch(() => '');
    const hasBiz = treeText.includes('蓝鲸平台');
    console.log('=== 弹框业务树文本(截断) ===');
    console.log(treeText.replace(/\n+/g, ' | ').slice(0, 300));

    // 断言：选中主机所属模块（行数据 row.module 聚合）已被自动恢复勾选
    // （模块 ID 由清库后的生成序列动态决定，不做硬编码）
    const checkedState = await page.evaluate(() => {
      const vm = document.querySelector('.module-selector-layout') && document.querySelector('.module-selector-layout').__vue__
      if (!vm || !vm.$refs.tree) return { err: 'no tree vm' }
      const checked = vm.checked || []
      const first = checked[0]
      const node = first ? vm.$refs.tree.getNodeById(first.id) : null
      return {
        checkedCount: checked.length,
        firstId: first ? first.id : null,
        nodeChecked: node ? node.checked : false,
        vmChecked: checked.map(n => n && n.id)
      }
    })

    const typeErrors = errors.filter(e => e.includes('Cannot read properties of undefined'));
    console.log('\n=== 断言结果 ===');
    console.log('业务树渲染出 biz 节点:', hasBiz);
    console.log('懒加载请求数:', requests.length, requests.slice(0, 5));
    console.log('默认模块恢复勾选:', JSON.stringify(checkedState));
    console.log('TypeError 数量:', typeErrors.length);
    console.log('JS 运行时错误:', errors.length);
    if (errors.length) console.log(errors.slice(0, 5).join('\n'));

    const pass = hasBiz
      && typeErrors.length === 0
      && errors.length === 0
      && requests.length === 0             // 全量树：不再发 /topo/instance/children|path 懒加载请求
      && checkedState.checkedCount >= 1
      && checkedState.nodeChecked === true; // 选中主机所属模块被自动恢复勾选（ID 由行数据动态决定）
    console.log(pass ? '\n✅ SMOKE PASS' : '\n❌ SMOKE FAIL');
    process.exit(pass ? 0 : 1);
  } catch (e) {
    console.log('❌ SMOKE ERROR:', e.message);
    console.log('已收集错误:', errors.slice(0, 5).join('\n'));
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
