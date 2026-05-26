const { test, expect } = require('@playwright/test');

test('实例列表页面加载和控制台日志', async ({ page }) => {
  const consoleMessages = [];
  const consoleErrors = [];
  
  page.on('console', msg => {
    const text = msg.text();
    consoleMessages.push({ type: msg.type(), text });
    if (msg.type() === 'error') {
      consoleErrors.push(text);
    }
  });
  
  // 1. 访问首页
  console.log('1. 访问首页...');
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  
  // 2. 点击交换机卡片进入实例列表
  console.log('2. 点击交换机卡片...');
  const switchCard = page.locator('.resource-card').first();
  await switchCard.click();
  await page.waitForTimeout(2000);
  
  // 3. 等待网络请求完成
  console.log('3. 等待数据加载...');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(3000);
  
  // 输出控制台消息
  console.log('\n=== 控制台消息 ===');
  consoleMessages.forEach(msg => {
    if (msg.text.includes('DEBUG') || msg.text.includes('Error') || msg.text.includes('错误')) {
      console.log(`[${msg.type}] ${msg.text}`);
    }
  });
  
  if (consoleErrors.length > 0) {
    console.log('\n=== 错误消息 ===');
    consoleErrors.forEach(err => console.log(err));
  } else {
    console.log('\n没有控制台错误');
  }
  
  // 截图
  await page.screenshot({ path: 'instance-list-test.png', fullPage: true });
  console.log('\n截图已保存: instance-list-test.png');
});
