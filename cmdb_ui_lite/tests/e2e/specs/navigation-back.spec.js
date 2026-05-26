/**
 * 导航返回功能测试
 * Navigation Back Functionality Test
 */
const { test, expect } = require('@playwright/test');

test.describe('导航返回功能测试', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3001/');
    await page.waitForLoadState('networkidle');
  });

  test('TC-NAV-001: 资源首页显示模型卡片', async ({ page }) => {
    // 验证资源首页显示资源目录
    const header = await page.textContent('h2');
    expect(header).toBe('资源目录');

    // 验证显示模型卡片
    const cards = await page.$$('.resource-card');
    expect(cards.length).toBeGreaterThan(0);
  });

  test('TC-NAV-002: 点击模型卡片进入实例列表页', async ({ page }) => {
    // 点击第一个模型卡片
    await page.click('.resource-card:first-child');
    await page.waitForTimeout(500);

    // 验证进入实例列表页
    const url = page.url();
    expect(url).toContain('/instance/');

    // 验证显示返回按钮
    const backButton = await page.$('.header-back');
    expect(backButton).not.toBeNull();

    // 验证显示模型名称
    const pageTitle = await page.textContent('.page-title');
    expect(pageTitle).toBeTruthy();
  });

  test('TC-NAV-003: 实例列表页返回资源首页', async ({ page }) => {
    // 进入实例列表页
    await page.click('.resource-card:first-child');
    await page.waitForTimeout(500);

    // 点击返回按钮
    await page.click('.header-back');
    await page.waitForTimeout(500);

    // 验证返回资源首页
    const url = page.url();
    expect(url).toBe('http://localhost:3001/');

    // 验证资源目录显示正常
    const header = await page.textContent('h2');
    expect(header).toBe('资源目录');

    // 验证模型卡片仍然显示
    const cards = await page.$$('.resource-card');
    expect(cards.length).toBeGreaterThan(0);
  });

  test('TC-NAV-004: 详情页返回实例列表页', async ({ page }) => {
    // 进入实例列表页
    await page.click('.resource-card:first-child');
    await page.waitForTimeout(500);

    // 点击第一个实例的ID
    const firstIdButton = await page.$('.bk-table-body-wrapper tbody tr:first-child td:nth-child(2) button');
    if (firstIdButton) {
      await firstIdButton.click();
      await page.waitForTimeout(500);

      // 验证进入详情页
      const detailsUrl = page.url();
      expect(detailsUrl).toContain('/instance/');

      // 点击返回按钮
      await page.click('.header-back');
      await page.waitForTimeout(500);

      // 验证返回实例列表页
      const url = page.url();
      expect(url).toContain('/instance/');
      expect(url).not.toContain('/instance/' + /\/[0-9]+$/);
    }
  });

  test('TC-NAV-005: 从实例列表页返回后卡片仍可点击', async ({ page }) => {
    // 进入实例列表页
    await page.click('.resource-card:first-child');
    await page.waitForTimeout(500);

    // 返回资源首页
    await page.click('.header-back');
    await page.waitForTimeout(500);

    // 再次点击模型卡片
    await page.click('.resource-card:first-child');
    await page.waitForTimeout(500);

    // 验证仍能进入实例列表页
    const url = page.url();
    expect(url).toContain('/instance/');

    // 验证表格数据正常显示
    const rows = await page.$$('.bk-table-body-wrapper tbody tr');
    expect(rows.length).toBeGreaterThan(0);
  });
});
