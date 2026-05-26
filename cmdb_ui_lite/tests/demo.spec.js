const { test, expect } = require('@playwright/test');

test('首页加载和控制台日志测试', async ({ page }) => {
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
  console.log('页面加载完成');
  
  const title = await page.title();
  console.log('页面标题:', title);
  
  await page.waitForTimeout(3000);
  
  console.log('\n=== 控制台消息 ===');
  consoleMessages.forEach(msg => {
    console.log(`[${msg.type}] ${msg.text}`);
  });
  
  if (consoleErrors.length > 0) {
    console.log('\n=== 错误 ===');
    consoleErrors.forEach(err => console.log(err));
  }
  
  await page.screenshot({ path: 'test-result.png', fullPage: true });
  console.log('\n截图已保存: test-result.png');
});
