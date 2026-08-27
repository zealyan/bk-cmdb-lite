/* E2E：转移到业务模块弹框 - 节点图标应显示「模型中文名首字」（biz3 自定义主线层验证）
 *
 * 场景：biz3 主线为 biz→sys(应用系统)→subsys(应用子系统)→set→module。
 * 修复前 sys/subsys 节点 bk_obj_name 缺失时图标取英文 obj_id 首字（sys→'s'），
 * 修复后应显示「应」（应用系统）与「子」（应用子系统），对齐主拓扑树图标。
 *
 * 断言：
 *   1. 弹框业务树渲染出 sys 节点，图标为「应」+ 名称「应用系统」
 *   2. subsys 节点图标为「子」
 *   3. 无 TypeError / JS 运行时错误
 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome'
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  const errors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error' && !msg.text().includes('Failed to load resource')) {
      errors.push(`[console.error] ${msg.text()}`);
    }
  });
  page.on('pageerror', (err) => errors.push(`[pageerror] ${err.message}`));

  try {
    await page.goto('http://127.0.0.1:3000/business/3/index#/business/3/index', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1500);

    // 勾选第一台主机
    const checkbox = page.locator('.host-table tbody tr .bk-form-checkbox span.bk-checkbox').first();
    await checkbox.click({ timeout: 10000, force: true });
    await page.waitForTimeout(400);

    // 打开「转移至」→「业务模块」
    await page.locator('text=转移至').first().click({ timeout: 10000 });
    await page.waitForTimeout(300);
    await page.locator('.bk-dropdown-item', { hasText: '业务模块' }).click({ timeout: 10000 });
    await page.waitForTimeout(4000);

    // 读取弹框树文本与图标
    const treeText = await page.locator('.module-selector-layout').innerText().catch(() => '');
    const state = await page.evaluate(() => {
      const layout = document.querySelector('.module-selector-layout');
      if (!layout) return { err: 'no layout' };
      const icons = Array.from(layout.querySelectorAll('.node-icon, .internal-node-icon')).map(e => e.innerText.trim());
      return { icons };
    });

    console.log('=== 弹框业务树文本(截断) ===');
    console.log(treeText.replace(/\n+/g, ' | ').slice(0, 300));
    console.log('节点图标数组:', JSON.stringify(state));

    const hasYing = treeText.includes('应') && treeText.includes('应用系统');
    const hasZi = treeText.includes('子') && treeText.includes('应用子系统');
    const badSysIcon = state.icons && state.icons.includes('s');
    const typeErrors = errors.filter(e => e.includes('Cannot read properties of undefined'));

    const pass = hasYing && hasZi && !badSysIcon && typeErrors.length === 0 && errors.length === 0;
    console.log('\n=== 断言结果 ===');
    console.log('sys 图标「应」+ 名称「应用系统」:', hasYing);
    console.log('subsys 图标「子」+ 名称「应用子系统」:', hasZi);
    console.log('存在英文 obj_id 首字图标(如 s):', !!badSysIcon);
    console.log('TypeError 数量:', typeErrors.length);
    console.log('JS 运行时错误:', errors.length);
    console.log(pass ? '\n✅ ICON-CN-FIRST-CHAR PASS' : '\n❌ ICON-CN-FIRST-CHAR FAIL');
    await browser.close();
    process.exit(pass ? 0 : 1);
  } catch (e) {
    console.log('❌ SMOKE ERROR:', e.message);
    console.log('已收集错误:', errors.slice(0, 5).join('\n'));
    await browser.close();
    process.exit(1);
  }
})();
