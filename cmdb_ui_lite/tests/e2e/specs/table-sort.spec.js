/**
 * 表格排序功能测试
 * Table Sorting Feature Test
 */
const { test, expect } = require('@playwright/test');
const { InstanceListPage } = require('../page-objects/instance-list.page');

test.describe('表格排序功能测试', () => {
  let instanceListPage;

  test.beforeEach(async ({ page }) => {
    instanceListPage = new InstanceListPage(page);
    await instanceListPage.navigateToModel('bk_slb');
  });

  test('TC-001: 表格列显示排序图标', async () => {
    // 验证表格列标题存在
    const headers = await instanceListPage.getTableHeaders();
    expect(headers.length).toBeGreaterThan(0);

    // 验证排序图标存在
    const sortIcon = await instanceListPage.page.$('.bk-table-sort-caret, .caret-wrapper');
    expect(sortIcon).not.toBeNull();
  });

  test('TC-002: 点击列标题触发升序排序', async ({ page }) => {
    // 获取排序前第一行数据
    const beforeSort = await instanceListPage.getFirstRowData();
    const idBefore = parseInt(beforeSort[1]);

    // 点击ID列标题
    await instanceListPage.clickColumnHeader(1);

    // 验证排序状态
    const sortState = await instanceListPage.getSortState(1);
    expect(sortState).toBe('ascending');
  });

  test('TC-003: 再次点击列标题切换为降序', async ({ page }) => {
    // 第一次点击 - 升序
    await instanceListPage.clickColumnHeader(1);

    // 第二次点击 - 降序
    await instanceListPage.clickColumnHeader(1);

    // 验证排序状态
    const sortState = await instanceListPage.getSortState(1);
    expect(sortState).toBe('descending');
  });

  test('TC-004: 点击不同列触发排序', async ({ page }) => {
    // 点击第三列（SLB名称）
    await instanceListPage.clickColumnHeader(2);

    // 验证排序状态
    const sortState = await instanceListPage.getSortState(2);
    expect(sortState).toBe('ascending');
  });

  test('TC-005: 排序后翻页保持排序状态', async ({ page }) => {
    // 设置排序
    await instanceListPage.clickColumnHeader(1);
    await instanceListPage.clickColumnHeader(1); // 降序

    // 获取排序状态
    const sortStateBefore = await instanceListPage.getSortState(1);

    // 翻页
    await instanceListPage.goToNextPage();
    await page.waitForTimeout(500);

    // 验证排序状态保持
    const sortStateAfter = await instanceListPage.getSortState(1);
    expect(sortStateAfter).toBe(sortStateBefore);
  });
});
