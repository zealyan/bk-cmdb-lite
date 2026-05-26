const { test, expect } = require('@playwright/test');

test('面包屑导航返回时搜索状态保持测试', async ({ page }) => {
  const consoleLogs = [];

  page.on('console', msg => {
    consoleLogs.push({ type: msg.type(), text: msg.text() });
  });

  console.log('\n========== 面包屑导航返回测试 ==========\n');

  // 1. 访问交换机列表
  console.log('1. 访问交换机列表页面');
  await page.goto('http://localhost:3000/#/instance/bk_switch');
  await page.waitForTimeout(3000);

  // 2. 选择搜索字段
  console.log('2. 选择搜索字段');
  const fieldSelector = page.locator('.filter-selector .bk-select');
  await fieldSelector.click();
  await page.waitForTimeout(500);
  const options = page.locator('.bk-options .bk-option');
  await options.first().click();
  await page.waitForTimeout(500);

  // 3. 输入中文关键词并搜索
  const chineseKeyword = '服务器';
  console.log(`3. 输入中文关键词: "${chineseKeyword}" 并搜索`);
  const searchInput = page.locator('.filter-value input');
  await searchInput.fill(chineseKeyword);
  await page.waitForTimeout(300);

  const searchButton = page.locator('.search-btn');
  await searchButton.click();
  await page.waitForTimeout(3000);

  const urlAfterSearch = page.url();
  console.log(`   搜索后URL: ${urlAfterSearch}`);

  // 4. 进入详情页
  console.log('4. 进入详情页');
  const viewButton = page.locator('.bk-table .bk-button').filter({ hasText: '查看' }).first();
  const hasViewButton = await viewButton.count() > 0;

  if (hasViewButton) {
    await viewButton.click();
    await page.waitForTimeout(3000);

    const urlInDetails = page.url();
    console.log(`   详情页URL: ${urlInDetails}`);

    // 5. 点击面包屑中的模型名称返回列表
    console.log('5. 点击面包屑中的模型名称返回列表');
    const modelNameLink = page.locator('.breadcrumb-item').filter({ hasText: '交换机' });
    const hasModelLink = await modelNameLink.count() > 0;

    if (hasModelLink) {
      await modelNameLink.click();
      await page.waitForTimeout(3000);

      const urlAfterReturn = page.url();
      console.log(`   返回后URL: ${urlAfterReturn}`);

      // 6. 检查搜索状态是否恢复
      console.log('6. 检查搜索状态是否恢复');

      const searchInputAfter = page.locator('.filter-value input');
      const restoredValue = await searchInputAfter.inputValue();
      console.log(`   返回后输入框值: "${restoredValue}"`);

      const stateRestored = restoredValue === chineseKeyword;
      console.log(`   状态恢复: ${stateRestored ? '✅ 成功' : '❌ 失败'}`);

      // 总结
      console.log('\n========== 测试总结 ==========\n');
      console.log('进入详情页:', '✅ 成功');
      console.log('面包屑返回:', '✅ 成功');
      console.log('状态恢复:', stateRestored ? '✅ 成功' : '❌ 失败');

      expect(stateRestored).toBe(true);
    } else {
      console.log('⚠️ 未找到面包屑中的模型名称链接');
      expect(false).toBe(true);
    }
  } else {
    console.log('⚠️ 未找到查看按钮（可能没有数据）');
    expect(false).toBe(true);
  }
});

test('面包屑返回按钮测试', async ({ page }) => {
  console.log('\n========== 面包屑返回按钮测试 ==========\n');

  // 1. 访问交换机列表
  console.log('1. 访问交换机列表');
  await page.goto('http://localhost:3000/#/instance/bk_switch');
  await page.waitForTimeout(3000);

  // 2. 搜索
  const fieldSelector = page.locator('.filter-selector .bk-select');
  await fieldSelector.click();
  await page.waitForTimeout(500);
  const options = page.locator('.bk-options .bk-option');
  await options.first().click();
  await page.waitForTimeout(500);

  const searchInput = page.locator('.filter-value input');
  await searchInput.fill('测试');
  await page.waitForTimeout(300);

  const searchButton = page.locator('.search-btn');
  await searchButton.click();
  await page.waitForTimeout(3000);

  console.log('2. 搜索完成，URL:', page.url());

  // 3. 进入详情页
  console.log('3. 进入详情页');
  const viewButton = page.locator('.bk-table .bk-button').filter({ hasText: '查看' }).first();
  await viewButton.click();
  await page.waitForTimeout(3000);
  console.log('   详情页URL:', page.url());

  // 4. 点击返回按钮
  console.log('4. 点击面包屑返回按钮');
  const backButton = page.locator('.page-breadcrumbs .icon');
  await backButton.click();
  await page.waitForTimeout(3000);

  console.log('   返回后URL:', page.url());

  // 5. 检查状态
  const restoredValue = await searchInput.inputValue();
  console.log('   输入框值:', restoredValue);

  const stateRestored = restoredValue === '测试';
  console.log('   状态恢复:', stateRestored ? '✅ 成功' : '❌ 失败');

  expect(stateRestored).toBe(true);
});
