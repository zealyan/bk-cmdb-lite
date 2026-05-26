const { test, expect } = require('@playwright/test');

test('详细调试Alert问题', async ({ page }) => {
  // 监听所有控制台消息
  const consoleLogs = [];
  page.on('console', msg => {
    const log = `[${msg.type().toUpperCase()}] ${msg.text()}`;
    consoleLogs.push(log);
    console.log(log);
  });
  
  // 监听所有网络请求
  const networkRequests = [];
  page.on('request', req => {
    networkRequests.push(`${req.method()} ${req.url()}`);
    console.log(`[NETWORK REQUEST] ${req.method()} ${req.url()}`);
  });
  
  // 监听所有网络响应
  page.on('response', res => {
    console.log(`[NETWORK RESPONSE] ${res.status()} ${res.url()}`);
  });

  console.log('\n=== 开始测试 ===\n');
  
  // 1. 访问首页
  console.log('步骤1: 访问 http://localhost:3000/');
  await page.goto('http://localhost:3000/', { waitUntil: 'networkidle' });
  
  // 2. 等待足够长的时间
  console.log('\n步骤2: 等待5秒让mounted钩子执行...');
  await page.waitForTimeout(5000);
  
  // 3. 打印所有控制台日志
  console.log('\n=== 控制台日志 ===');
  consoleLogs.forEach(log => console.log(log));
  
  // 4. 打印网络请求
  console.log('\n=== 网络请求 ===');
  networkRequests.forEach(req => console.log(req));
  
  // 5. 检查页面内容
  console.log('\n步骤3: 检查页面...');
  const pageContent = await page.content();
  console.log('页面包含"资源目录":', pageContent.includes('资源目录'));
  
  // 6. 手动触发alert测试
  console.log('\n步骤4: 手动测试alert...');
  const alertResult = await page.evaluate(() => {
    try {
      window.alert('这是手动触发的测试alert');
      return 'alert成功执行';
    } catch (e) {
      return 'alert执行失败: ' + e.message;
    }
  });
  console.log('手动alert结果:', alertResult);
  await page.waitForTimeout(1000);
  
  console.log('\n=== 测试完成 ===');
  expect(alertResult).toBe('alert成功执行');
});