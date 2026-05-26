const { test, expect } = require('@playwright/test');

test('检查SLB服务器数据加载', async ({ page }) => {
  // 监听所有控制台消息
  const consoleLogs = [];
  page.on('console', msg => {
    consoleLogs.push(`[${msg.type()}] ${msg.text()}`);
    console.log(`[CONSOLE ${msg.type()}] ${msg.text()}`);
  });

  console.log('\n=== 测试开始 ===\n');
  
  // 1. 访问SLB服务器页面
  console.log('步骤1: 访问 http://localhost:3000/#/instance/bk_slb_server');
  await page.goto('http://localhost:3000/#/instance/bk_slb_server');
  
  // 2. 等待数据加载
  console.log('\n步骤2: 等待3秒让数据加载...');
  await page.waitForTimeout(3000);
  
  // 3. 检查控制台日志
  console.log('\n=== 控制台日志 ===');
  consoleLogs.forEach(log => console.log(log));
  
  // 4. 检查表格数据
  console.log('\n步骤3: 检查表格...');
  const tableVisible = await page.locator('.bk-table').isVisible({ timeout: 5000 }).catch(() => false);
  console.log('表格可见:', tableVisible);
  
  // 5. 检查表格行数
  const rows = await page.locator('.bk-table tbody tr').count();
  console.log('表格行数:', rows);
  
  // 6. 检查是否有无数据提示
  const emptyText = await page.locator('.bk-table-empty-text, .bk-table__empty, [class*="empty"]').textContent({ timeout: 2000 }).catch(() => '无此元素');
  console.log('空数据提示:', emptyText);
  
  console.log('\n=== 测试完成 ===');
});