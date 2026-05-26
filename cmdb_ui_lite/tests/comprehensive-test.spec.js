const { test, expect } = require('@playwright/test');

test('综合测试 - 首页alert和SLB数据', async ({ page }) => {
  // 监听控制台
  const consoleLogs = [];
  page.on('console', msg => {
    consoleLogs.push(`[${msg.type()}] ${msg.text()}`);
  });

  console.log('\n=== 测试1: 首页alert ===\n');
  await page.goto('http://localhost:3000/');
  await page.waitForTimeout(3000);
  
  const hasDebugLog = consoleLogs.some(log => log.includes('[DEBUG]'));
  console.log('首页DEBUG日志:', hasDebugLog ? '有' : '无');
  console.log('首页alert执行:', hasDebugLog ? '是' : '否');

  console.log('\n=== 测试2: SLB服务器数据 ===\n');
  await page.goto('http://localhost:3000/#/instance/bk_slb_server');
  await page.waitForTimeout(3000);
  
  const hasSLBLog = consoleLogs.some(log => log.includes('实例数:'));
  console.log('SLB数据日志:', hasSLBLog ? '有' : '无');
  
  console.log('\n=== 总结 ===');
  console.log('首页alert执行:', hasDebugLog ? '✅ 成功' : '❌ 未执行');
  console.log('SLB数据加载:', hasSLBLog ? '✅ 成功' : '❌ 失败');
  
  expect(hasDebugLog).toBe(true);
  expect(hasSLBLog).toBe(true);
});