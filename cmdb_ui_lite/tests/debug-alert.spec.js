const { test, expect } = require('@playwright/test');

test('Debug Homepage Alert Issue', async ({ page }) => {
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

  console.log('开始测试...');
  
  // 访问首页
  await page.goto('http://localhost:3000/');
  
  // 等待几秒钟
  await page.waitForTimeout(3000);
  
  // 打印所有控制台日志
  console.log('\n=== 控制台日志 ===');
  consoleLogs.forEach(log => console.log(log));
  
  // 尝试手动触发mounted
  console.log('\n=== 尝试触发alert ===');
  const result = await page.evaluate(async () => {
    try {
      const response = await fetch('http://localhost:8000/health');
      const data = await response.json();
      alert(`手动测试: 后端健康状态 = ${data.status}`);
      return { success: true, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
  
  console.log('手动触发结果:', result);
  
  // 检查是否有alert对话框
  await page.waitForTimeout(1000);
  
  console.log('\n=== 测试完成 ===');
});