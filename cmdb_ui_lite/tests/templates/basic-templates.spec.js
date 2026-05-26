/**
 * CMDB UI Lite - Playwright 测试模板
 * 
 * 使用方法:
 * 1. 确保后端服务在 http://localhost:8000
 * 2. 确保前端服务在 http://localhost:3000
 * 3. 执行: ./node_modules/.bin/playwright test tests/templates/
 */

const { test, expect } = require('@playwright/test');

// ============ 基础测试模板 ============

/**
 * 模板1: 基础页面加载测试
 */
test('T1-基础页面加载测试', async ({ page }) => {
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  expect(await page.title()).toBe('CMDB UI Lite');
  
  await page.waitForTimeout(1000);
  await page.screenshot({ path: 'test-T1-basic-load.png' });
  
  if (errors.length > 0) {
    console.log('控制台错误:', errors);
    throw new Error('存在控制台错误');
  }
});

/**
 * 模板2: 资源卡片显示测试
 */
test('T2-资源卡片显示测试', async ({ page }) => {
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  
  // 验证卡片数量
  const cards = page.locator('.resource-card');
  const count = await cards.count();
  expect(count).toBeGreaterThan(0);
  console.log(`发现 ${count} 个资源卡片`);
  
  // 验证卡片内容
  const firstCardText = await cards.first().textContent();
  expect(firstCardText.length).toBeGreaterThan(0);
});

/**
 * 模板3: 导航到实例列表
 */
test('T3-导航到实例列表', async ({ page }) => {
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  
  // 点击第一个卡片
  await page.locator('.resource-card').first().click();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);
  
  // 验证URL变化
  expect(page.url()).toContain('/instance/');
  console.log('当前URL:', page.url());
  
  await page.screenshot({ path: 'test-T3-instance-list.png' });
});

// ============ 功能测试模板 ============

/**
 * 模板4: 控制台Debug日志验证
 */
test('T4-控制台Debug日志验证', async ({ page }) => {
  const debugLogs = [];
  page.on('console', msg => {
    if (msg.text().includes('[DEBUG]')) {
      debugLogs.push(msg.text());
    }
  });
  
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  await page.locator('.resource-card').first().click();
  await page.waitForTimeout(3000);
  
  console.log('\n=== Debug 日志 ===');
  debugLogs.forEach(log => console.log(log));
  
  // 验证数据加载完成
  const hasDataLoaded = debugLogs.some(log => log.includes('数据加载完成'));
  expect(hasDataLoaded).toBe(true);
});

/**
 * 模板5: 搜索功能测试
 */
test('T5-搜索功能测试', async ({ page }) => {
  await page.goto('http://localhost:3000/#/instance/bk_switch', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  
  // 输入搜索词
  const searchInput = page.locator('.bk-input input').first();
  await searchInput.fill('core');
  await searchInput.press('Enter');
  
  await page.waitForTimeout(2000);
  
  // 截图保存搜索结果
  await page.screenshot({ path: 'test-T5-search-result.png' });
  
  console.log('搜索完成');
});

/**
 * 模板6: 分页功能测试
 */
test('T6-分页功能测试', async ({ page }) => {
  await page.goto('http://localhost:3000/#/instance/bk_switch', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  
  // 查找分页组件
  const pagination = page.locator('.bk-page');
  const isPaginationVisible = await pagination.isVisible().catch(() => false);
  
  if (isPaginationVisible) {
    console.log('分页组件可见');
    
    // 点击下一页
    const nextButton = page.locator('.bk-page button').filter({ hasText: '下一页' });
    const isNextEnabled = await nextButton.isEnabled().catch(() => false);
    
    if (isNextEnabled) {
      await nextButton.click();
      await page.waitForTimeout(1000);
      console.log('已点击下一页');
    }
  } else {
    console.log('分页组件不可见（数据量少）');
  }
});

// ============ 详情页测试模板 ============

/**
 * 模板7: 实例详情页测试
 */
test('T7-实例详情页测试', async ({ page }) => {
  await page.goto('http://localhost:3000/#/instance/bk_switch/1', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  
  // 验证页面标题
  const pageTitle = await page.locator('.detail-header h3').textContent().catch(() => '');
  console.log('详情页标题:', pageTitle);
  
  await page.screenshot({ path: 'test-T7-instance-detail.png' });
});

/**
 * 模板8: 关联Tab测试
 */
test('T8-关联Tab测试', async ({ page }) => {
  await page.goto('http://localhost:3000/#/instance/bk_switch/1', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  
  // 点击关联标签
  const associationTab = page.locator('.bk-tab-label').filter({ hasText: '关联' });
  if (await associationTab.isVisible()) {
    await associationTab.click();
    await page.waitForTimeout(1000);
    console.log('已点击关联标签');
  }
  
  await page.screenshot({ path: 'test-T8-association-tab.png' });
});

// ============ API 验证测试模板 ============

/**
 * 模板9: API 响应验证测试
 */
test('T9-API响应验证测试', async ({ page }) => {
  // 这个测试验证后端API是否正常
  const apiResponse = await page.request.get('http://localhost:8000/api/models');
  expect(apiResponse.ok()).toBe(true);
  
  const data = await apiResponse.json();
  expect(data.models).toBeDefined();
  expect(Array.isArray(data.models)).toBe(true);
  expect(data.models.length).toBeGreaterThan(0);
  
  console.log('API模型数量:', data.models.length);
});

// ============ 快速冒烟测试 ============

/**
 * 冒烟测试: 核心功能快速验证
 */
test.describe('冒烟测试 - Smoke Tests', () => {
  test('首页可访问', async ({ page }) => {
    const response = await page.goto('http://localhost:3000');
    expect(response.status()).toBe(200);
  });
  
  test('后端API健康', async ({ page }) => {
    const response = await page.request.get('http://localhost:8000/health');
    expect(response.ok()).toBe(true);
  });
  
  test('可导航到实例列表', async ({ page }) => {
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await page.locator('.resource-card').first().click();
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/instance/');
  });
});
