const { test, expect } = require('@playwright/test');

test('测试window.alert是否工作', async ({ page }) => {
  console.log('测试开始...');
  
  // 1. 访问首页
  await page.goto('http://localhost:3000/');
  console.log('已访问首页');
  
  // 2. 等待2秒
  await page.waitForTimeout(2000);
  console.log('已等待2秒');
  
  // 3. 直接执行alert测试
  console.log('准备执行window.alert测试...');
  const result = await page.evaluate(() => {
    try {
      window.alert('测试alert - 如果您看到这个对话框，说明alert功能正常！');
      console.log('alert已执行');
      return 'success';
    } catch (error) {
      console.error('alert执行失败:', error);
      return 'failed: ' + error.message;
    }
  });
  
  console.log('Alert测试结果:', result);
  
  // 等待1秒看alert
  await page.waitForTimeout(1000);
  
  // 验证结果
  expect(result).toBe('success');
});