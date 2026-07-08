const { test, expect } = require('@playwright/test');

test('验证业务拓扑树页面', async ({ page }) => {
  // 访问业务拓扑页面
  await page.goto('http://localhost:3000/#/business/topology');
  
  // 等待页面加载完成
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);
  
  // 截图保存
  await page.screenshot({ path: '/data/tool/browser_snapshots/business-topology-tree.png', fullPage: true });
  
  // 检查拓扑树是否存在
  const treeWrapper = await page.locator('.topology-tree-wrapper');
  await expect(treeWrapper).toBeVisible();
  
  // 检查搜索输入框
  const searchInput = await page.locator('.tree-search input');
  await expect(searchInput).toBeVisible();
  
  // 检查树节点数量（至少有业务节点）
  const treeNodes = await page.locator('.topology-tree-node');
  const nodeCount = await treeNodes.count();
  expect(nodeCount).toBeGreaterThan(0);
  
  // 检查右侧Tab面板
  const tabPanels = await page.locator('.bk-tab-panel');
  const panelCount = await tabPanels.count();
  expect(panelCount).toBeGreaterThan(0);
  
  console.log(`拓扑树验证成功！树节点数量: ${nodeCount}, Tab面板数量: ${panelCount}`);
});