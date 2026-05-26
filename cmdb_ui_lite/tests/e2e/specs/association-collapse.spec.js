/**
 * 关联组件折叠功能测试
 * Association Component Collapse Feature Test
 */
const { test, expect } = require('@playwright/test');
const { InstanceDetailsPage } = require('../page-objects/instance-details.page');

test.describe('关联组件折叠功能测试', () => {
  let instanceDetailsPage;

  test.beforeEach(async ({ page }) => {
    instanceDetailsPage = new InstanceDetailsPage(page);
    await instanceDetailsPage.navigateToInstance('bk_slb', 1);
  });

  test('TC-006: 详情页显示关联Tab', async () => {
    // 验证关联tab存在
    const isVisible = await instanceDetailsPage.isAssociationTabVisible();
    expect(isVisible).toBeTruthy();
  });

  test('TC-007: 点击关联Tab显示关联列表', async () => {
    // 点击关联tab
    await instanceDetailsPage.clickAssociationTab();

    // 验证关联分组存在
    const groups = await instanceDetailsPage.getAssociationGroups();
    expect(groups.length).toBeGreaterThan(0);
  });

  test('TC-008: 显示SLB后端服务器和SLB监听器分组', async () => {
    await instanceDetailsPage.clickAssociationTab();

    const groups = await instanceDetailsPage.getAssociationGroups();
    const groupTitles = groups.map(g => g.title);

    // 验证包含两个分组
    expect(groupTitles).toContain('SLB后端服务器');
    expect(groupTitles).toContain('SLB监听器');
  });

  test('TC-009: 分组默认展开状态', async () => {
    await instanceDetailsPage.clickAssociationTab();

    // 验证第一个分组是展开的
    const state = await instanceDetailsPage.getGroupSortState(0);
    expect(state).toBe('expanded');
  });

  test('TC-010: 点击分组标题收起表格', async ({ page }) => {
    await instanceDetailsPage.clickAssociationTab();

    // 获取点击前状态
    const stateBefore = await instanceDetailsPage.getGroupSortState(0);
    expect(stateBefore).toBe('expanded');

    // 点击分组标题
    await instanceDetailsPage.clickAssociationGroup(0);

    // 验证收起状态
    const stateAfter = await instanceDetailsPage.getGroupSortState(0);
    expect(stateAfter).toBe('collapsed');
  });

  test('TC-011: 再次点击分组标题展开表格', async ({ page }) => {
    await instanceDetailsPage.clickAssociationTab();

    // 收起
    await instanceDetailsPage.clickAssociationGroup(0);

    // 展开
    await instanceDetailsPage.clickAssociationGroup(0);

    // 验证展开状态
    const state = await instanceDetailsPage.getGroupSortState(0);
    expect(state).toBe('expanded');
  });

  test('TC-012: 多个分组独立控制展开收起', async ({ page }) => {
    await instanceDetailsPage.clickAssociationTab();

    // 收起第一个分组
    await instanceDetailsPage.clickAssociationGroup(0);
    const stateFirst = await instanceDetailsPage.getGroupSortState(0);

    // 验证第二个分组仍展开
    const stateSecond = await instanceDetailsPage.getGroupSortState(1);

    expect(stateFirst).toBe('collapsed');
    expect(stateSecond).toBe('expanded');
  });
});
