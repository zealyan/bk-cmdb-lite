const { test, expect } = require('@playwright/test');

test('详细的浏览器错误捕获测试', async ({ page, context }) => {
  const consoleLogs = [];
  const consoleErrors = [];
  const networkRequests = [];
  const networkResponses = [];

  page.on('console', msg => {
    consoleLogs.push({ type: msg.type(), text: msg.text() });
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  page.on('request', request => {
    networkRequests.push({
      method: request.method(),
      url: request.url(),
      resourceType: request.resourceType()
    });
  });

  page.on('response', async response => {
    try {
      networkResponses.push({
        url: response.url(),
        status: response.status(),
        ok: response.ok()
      });
    } catch (err) {
      console.log('无法获取响应详情:', err);
    }
  });

  page.on('pageerror', exception => {
    consoleErrors.push(`[Page Error] ${exception.message}`);
  });

  console.log('='.repeat(60));
  console.log('1. 访问实例列表页面');
  console.log('='.repeat(60));
  
  await page.goto('http://localhost:3000/#/instance/bk_switch', { 
    waitUntil: 'networkidle',
    timeout: 30000
  });

  console.log('\n页面标题:', await page.title());
  console.log('页面URL:', page.url());

  console.log('\n等待 5 秒让页面完全加载...');
  await page.waitForTimeout(5000);

  console.log('\n' + '='.repeat(60));
  console.log('2. 网络请求日志');
  console.log('='.repeat(60));
  networkRequests.forEach(req => {
    console.log(`[${req.method}] ${req.url}`);
  });

  console.log('\n' + '='.repeat(60));
  console.log('3. 网络响应日志');
  console.log('='.repeat(60));
  networkResponses.forEach(res => {
    console.log(`[${res.status}] ${res.url} ${res.ok ? '✓' : '✗'}`);
  });

  console.log('\n' + '='.repeat(60));
  console.log('4. 控制台日志');
  console.log('='.repeat(60));
  consoleLogs.forEach(log => {
    console.log(`[${log.type.toUpperCase()}] ${log.text}`);
  });

  console.log('\n' + '='.repeat(60));
  console.log('5. 控制台错误');
  console.log('='.repeat(60));
  if (consoleErrors.length > 0) {
    consoleErrors.forEach(err => console.log('✗ ' + err));
  } else {
    console.log('✓ 没有错误');
  }

  console.log('\n' + '='.repeat(60));
  console.log('6. 页面内容检查');
  console.log('='.repeat(60));

  try {
    const bodyText = await page.locator('body').textContent();
    console.log('页面包含"loading"文字:', bodyText.includes('loading'));
    console.log('页面包含"失败"文字:', bodyText.includes('失败'));
    console.log('页面包含"error"文字:', bodyText.toLowerCase().includes('error'));
  } catch (err) {
    console.log('无法获取页面文本:', err.message);
  }

  try {
    const tableExists = await page.locator('.bk-table').count() > 0;
    console.log('表格元素存在:', tableExists);
    
    if (tableExists) {
      const tableRows = await page.locator('.bk-table tbody tr').count();
      console.log('表格行数:', tableRows);
    }
  } catch (err) {
    console.log('表格检查失败:', err.message);
  }

  await page.screenshot({ path: '/workspace/bk-cmdb/debug-screenshot.png', fullPage: true });
  console.log('\n截图已保存: /workspace/bk-cmdb/debug-screenshot.png');

  console.log('\n' + '='.repeat(60));
  console.log('7. 检查网络请求详情');
  console.log('='.repeat(60));

  for (const req of networkRequests) {
    if (req.url.includes('api')) {
      console.log(`\nAPI请求: ${req.method} ${req.url}`);
    }
  }

  expect(consoleErrors.length).toBe(0);
});
