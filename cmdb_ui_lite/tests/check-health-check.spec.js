const { test, expect } = require('@playwright/test');

test('检查首页健康检查是否执行', async ({ page }) => {
  // 监听所有控制台消息
  const consoleLogs = [];
  page.on('console', msg => {
    consoleLogs.push(`[${msg.type()}] ${msg.text()}`);
    console.log(`[CONSOLE ${msg.type()}] ${msg.text()}`);
  });
  
  // 监听页面错误
  page.on('pageerror', error => {
    console.log(`[PAGE ERROR] ${error.message}`);
  });
  
  // 监听请求失败
  page.on('requestfailed', request => {
    console.log(`[REQUEST FAILED] ${request.url()} - ${request.failure().errorText}`);
  });

  console.log('\n=== 开始测试 ===\n');
  
  // 1. 访问首页
  console.log('步骤1: 访问 http://localhost:3000/');
  await page.goto('http://localhost:3000/');
  console.log('已访问');
  
  // 2. 等待3秒让mounted钩子执行
  console.log('\n步骤2: 等待3秒...');
  await page.waitForTimeout(3000);
  
  // 3. 检查控制台日志
  console.log('\n=== 控制台日志 ===');
  consoleLogs.forEach(log => console.log(log));
  
  // 4. 检查是否有DEBUG日志
  const hasDebugLog = consoleLogs.some(log => log.includes('[DEBUG]'));
  console.log('\n是否有DEBUG日志:', hasDebugLog);
  
  // 5. 检查页面是否包含资源目录
  console.log('\n步骤3: 检查页面...');
  const pageContent = await page.content();
  console.log('页面包含"资源目录":', pageContent.includes('资源目录'));
  
  // 6. 打印最终结果
  console.log('\n=== 测试完成 ===');
  console.log('健康检查是否执行:', hasDebugLog ? '是' : '否');
  
  // 断言
  if (!hasDebugLog) {
    console.log('\n警告：健康检查方法似乎没有被执行！');
  }
});