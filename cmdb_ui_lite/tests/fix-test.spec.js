const { test, expect } = require('@playwright/test');

test('实例列表页面数据加载测试', async ({ page }) => {
  const consoleMessages = [];
  const consoleErrors = [];

  page.on('console', msg => {
    const text = msg.text();
    consoleMessages.push({ type: msg.type(), text });
    if (msg.type() === 'error') {
      consoleErrors.push(text);
    }
  });

  console.log('开始访问首页...');
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });

  const title = await page.title();
  console.log('页面标题:', title);

  console.log('等待 2 秒...');
  await page.waitForTimeout(2000);

  console.log('点击交换机卡片...');
  try {
    const switchCard = page.locator('.resource-card').first();
    await switchCard.click();
    await page.waitForTimeout(3000);
  } catch (err) {
    console.log('无法通过点击导航，直接进入实例列表页面...');
    await page.goto('http://localhost:3000/#/instance/bk_switch', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
  }

  console.log('\n=== 控制台消息 ===');
  consoleMessages.forEach(msg => {
    if (msg.text.includes('[DEBUG]')) {
      console.log(`[${msg.type}] ${msg.text}`);
    }
  });

  if (consoleErrors.length > 0) {
    console.log('\n=== 错误消息 ===');
    consoleErrors.forEach(err => console.log(err));
  }

  await page.screenshot({ path: '/workspace/bk-cmdb/test-result.png', fullPage: true });
  console.log('\n截图已保存: /workspace/bk-cmdb/test-result.png');

  console.log('\n检查表格内容...');
  const tableRows = page.locator('.bk-table tbody tr');
  const rowCount = await tableRows.count();
  console.log('表格行数:', rowCount);

  if (rowCount > 0) {
    const firstRowText = await tableRows.first().textContent();
    console.log('第一行内容:', firstRowText);
  }

  expect(consoleErrors.length).toBe(0);
});
