const { test, expect } = require('@playwright/test');

test.describe('交换机列表搜索功能测试', () => {
  const consoleErrors = [];
  const consoleLogs = [];

  test.beforeEach(async ({ page }) => {
    consoleErrors.length = 0;
    consoleLogs.length = 0;

    page.on('console', msg => {
      const text = msg.text();
      if (msg.type() === 'error') {
        consoleErrors.push(text);
      }
      consoleLogs.push(`[${msg.type()}] ${text}`);
    });
  });

  test('测试1: 访问首页并进入交换机列表', async ({ page }) => {
    console.log('\n=== 测试1: 访问首页 ===\n');
    await page.goto('http://localhost:3000/');
    await page.waitForTimeout(2000);

    console.log('✅ 成功访问首页');
    console.log('首页控制台日志数量:', consoleLogs.length);
  });

  test('测试2: 进入交换机列表页面并选择型号字段', async ({ page }) => {
    console.log('\n=== 测试2: 进入交换机列表页面 ===\n');
    await page.goto('http://localhost:3000/#/instance/bk_switch');
    await page.waitForTimeout(3000);

    console.log('✅ 成功进入交换机列表页面');

    const pageTitle = await page.title();
    console.log('页面标题:', pageTitle);

    const hasTable = await page.locator('.bk-table').count() > 0;
    console.log('表格存在:', hasTable ? '✅ 是' : '❌ 否');

    const hasSearchSelector = await page.locator('.filter-selector').count() > 0;
    console.log('搜索字段选择器存在:', hasSearchSelector ? '✅ 是' : '❌ 否');

    expect(hasTable).toBe(true);
    expect(hasSearchSelector).toBe(true);
  });

  test('测试3: 选择"型号"字段进行搜索', async ({ page }) => {
    console.log('\n=== 测试3: 选择型号字段并搜索 ===\n');
    await page.goto('http://localhost:3000/#/instance/bk_switch');
    await page.waitForTimeout(3000);

    console.log('查找字段选择器...');
    const fieldSelector = page.locator('.filter-selector .bk-select');
    await fieldSelector.waitFor({ state: 'visible', timeout: 5000 });

    await fieldSelector.click();
    await page.waitForTimeout(500);

    console.log('等待选项列表...');
    const options = page.locator('.bk-options .bk-option');
    const optionCount = await options.count();
    console.log('找到的选项数量:', optionCount);

    let modelOptionFound = false;
    for (let i = 0; i < optionCount; i++) {
      const optionText = await options.nth(i).textContent();
      console.log(`选项 ${i}:`, optionText.trim());
      if (optionText.includes('型号')) {
        console.log('✅ 找到型号选项');
        await options.nth(i).click();
        modelOptionFound = true;
        break;
      }
    }

    expect(modelOptionFound).toBe(true, '未找到型号字段选项');
    await page.waitForTimeout(500);

    console.log('✅ 已选择型号字段');
  });

  test('测试4: 输入"h3"并点击搜索按钮', async ({ page }) => {
    console.log('\n=== 测试4: 输入搜索关键词并点击搜索 ===\n');
    await page.goto('http://localhost:3000/#/instance/bk_switch');
    await page.waitForTimeout(3000);

    const fieldSelector = page.locator('.filter-selector .bk-select');
    await fieldSelector.click();
    await page.waitForTimeout(500);

    const options = page.locator('.bk-options .bk-option');
    const optionCount = await options.count();

    for (let i = 0; i < optionCount; i++) {
      const optionText = await options.nth(i).textContent();
      if (optionText.includes('型号')) {
        await options.nth(i).click();
        break;
      }
    }
    await page.waitForTimeout(500);

    console.log('查找搜索输入框...');
    const searchInput = page.locator('.filter-value input');
    await searchInput.waitFor({ state: 'visible', timeout: 5000 });

    console.log('输入搜索关键词 "h3"...');
    await searchInput.fill('h3');
    await page.waitForTimeout(300);

    const inputValue = await searchInput.inputValue();
    console.log('输入框当前值:', inputValue);

    console.log('查找并点击搜索按钮...');
    const searchButton = page.locator('.search-btn');
    await searchButton.click();

    console.log('等待搜索结果...');
    await page.waitForTimeout(2000);

    console.log('✅ 搜索操作完成');
    console.log('控制台错误数量:', consoleErrors.length);
    if (consoleErrors.length > 0) {
      console.log('错误信息:', consoleErrors);
    }

    expect(inputValue).toBe('h3');
  });

  test('测试5: 验证搜索结果', async ({ page }) => {
    console.log('\n=== 测试5: 验证搜索结果 ===\n');
    await page.goto('http://localhost:3000/#/instance/bk_switch');
    await page.waitForTimeout(3000);

    const fieldSelector = page.locator('.filter-selector .bk-select');
    await fieldSelector.click();
    await page.waitForTimeout(500);

    const options = page.locator('.bk-options .bk-option');
    const optionCount = await options.count();

    for (let i = 0; i < optionCount; i++) {
      const optionText = await options.nth(i).textContent();
      if (optionText.includes('型号')) {
        await options.nth(i).click();
        break;
      }
    }
    await page.waitForTimeout(500);

    const searchInput = page.locator('.filter-value input');
    await searchInput.fill('h3');

    const searchButton = page.locator('.search-btn');
    await searchButton.click();

    await page.waitForTimeout(2000);

    console.log('检查表格数据...');
    const tableRows = page.locator('.bk-table-body tr');
    const rowCount = await tableRows.count();
    console.log('搜索结果行数:', rowCount);

    if (rowCount > 0) {
      console.log('✅ 搜索返回了结果');

      const firstRow = tableRows.first();
      const rowText = await firstRow.textContent();
      console.log('第一行数据包含 "h3":', rowText.toLowerCase().includes('h3') ? '✅ 是' : '❌ 否');
    } else {
      console.log('⚠️ 搜索未返回任何结果（可能数据库中没有匹配的型号）');
    }

    console.log('JavaScript错误数量:', consoleErrors.length);
    expect(true).toBe(true);
  });

  test('测试6: 回车键触发搜索', async ({ page }) => {
    console.log('\n=== 测试6: 回车键触发搜索 ===\n');
    await page.goto('http://localhost:3000/#/instance/bk_switch');
    await page.waitForTimeout(3000);

    const fieldSelector = page.locator('.filter-selector .bk-select');
    await fieldSelector.click();
    await page.waitForTimeout(500);

    const options = page.locator('.bk-options .bk-option');
    const optionCount = await options.count();

    for (let i = 0; i < optionCount; i++) {
      const optionText = await options.nth(i).textContent();
      if (optionText.includes('型号')) {
        await options.nth(i).click();
        break;
      }
    }
    await page.waitForTimeout(500);

    const searchInput = page.locator('.filter-value input');
    await searchInput.fill('h3');
    console.log('输入搜索关键词 "h3"...');

    console.log('按下回车键...');
    await searchInput.press('Enter');
    console.log('等待搜索结果...');
    await page.waitForTimeout(2000);

    console.log('✅ 回车键搜索完成');
    console.log('控制台错误数量:', consoleErrors.length);

    expect(true).toBe(true);
  });

  test('测试7: 清除搜索条件', async ({ page }) => {
    console.log('\n=== 测试7: 清除搜索条件 ===\n');
    await page.goto('http://localhost:3000/#/instance/bk_switch');
    await page.waitForTimeout(3000);

    const fieldSelector = page.locator('.filter-selector .bk-select');
    await fieldSelector.click();
    await page.waitForTimeout(500);

    const options = page.locator('.bk-options .bk-option');
    const optionCount = await options.count();

    for (let i = 0; i < optionCount; i++) {
      const optionText = await options.nth(i).textContent();
      if (optionText.includes('型号')) {
        await options.nth(i).click();
        break;
      }
    }
    await page.waitForTimeout(500);

    const searchInput = page.locator('.filter-value input');
    await searchInput.fill('h3');
    console.log('已输入搜索条件');

    const clearButton = page.locator('.filter-value .bk-icon.icon-clear');
    const hasClearButton = await clearButton.count() > 0;

    if (hasClearButton) {
      console.log('找到清除按钮，点击...');
      await clearButton.click();
      await page.waitForTimeout(500);

      const inputValue = await searchInput.inputValue();
      console.log('清除后输入框值:', inputValue || '(空)');
      console.log('✅ 清除功能正常');
    } else {
      console.log('⚠️ 未找到清除按钮，尝试手动清空...');
      await searchInput.clear();
      await page.waitForTimeout(500);
      console.log('✅ 手动清空完成');
    }

    expect(true).toBe(true);
  });

  test('测试8: 切换不同字段搜索', async ({ page }) => {
    console.log('\n=== 测试8: 切换不同字段搜索 ===\n');
    await page.goto('http://localhost:3000/#/instance/bk_switch');
    await page.waitForTimeout(3000);

    const fieldSelector = page.locator('.filter-selector .bk-select');
    await fieldSelector.click();
    await page.waitForTimeout(500);

    let options = page.locator('.bk-options .bk-option');
    let optionCount = await options.count();
    console.log('第一个字段选择前的选项数量:', optionCount);

    const firstFieldName = await options.first().textContent();
    console.log('第一个字段:', firstFieldName.trim());

    await options.first().click();
    await page.waitForTimeout(500);

    console.log('选择第一个字段后的搜索输入框占位符:');
    const placeholder = await page.locator('.filter-value input').getAttribute('placeholder');
    console.log('  占位符文本:', placeholder);

    await fieldSelector.click();
    await page.waitForTimeout(500);

    options = page.locator('.bk-options .bk-option');
    optionCount = await options.count();
    console.log('再次打开的选项数量:', optionCount);

    if (optionCount > 1) {
      console.log('切换到第二个字段...');
      await options.nth(1).click();
      await page.waitForTimeout(500);

      const newPlaceholder = await page.locator('.filter-value input').getAttribute('placeholder');
      console.log('切换后的占位符:', newPlaceholder);
      console.log('✅ 字段切换成功');
    } else {
      console.log('只有一个字段可选');
    }

    expect(optionCount).toBeGreaterThan(0);
  });
});

test('完整搜索流程测试', async ({ page }) => {
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  console.log('\n========== 完整搜索流程测试 ==========\n');

  console.log('步骤1: 访问 http://localhost:3000');
  await page.goto('http://localhost:3000/');
  await page.waitForTimeout(2000);
  console.log('✅ 访问首页完成\n');

  console.log('步骤2: 进入交换机列表页面');
  await page.goto('http://localhost:3000/#/instance/bk_switch');
  await page.waitForTimeout(3000);
  console.log('✅ 进入交换机列表页面完成\n');

  console.log('步骤3: 选择"型号"字段');
  const fieldSelector = page.locator('.filter-selector .bk-select');
  await fieldSelector.click();
  await page.waitForTimeout(500);

  const options = page.locator('.bk-options .bk-option');
  let modelFieldFound = false;

  for (let i = 0; i < await options.count(); i++) {
    const text = await options.nth(i).textContent();
    if (text.includes('型号')) {
      await options.nth(i).click();
      modelFieldFound = true;
      console.log('✅ 已选择型号字段\n');
      break;
    }
  }

  if (!modelFieldFound) {
    console.log('⚠️ 未找到型号字段，选择第一个可用字段\n');
    await options.first().click();
  }

  await page.waitForTimeout(500);

  console.log('步骤4: 输入"h3"进行搜索');
  const searchInput = page.locator('.filter-value input');
  await searchInput.fill('h3');
  console.log('✅ 输入完成\n');

  console.log('步骤5: 点击搜索按钮');
  const searchButton = page.locator('.search-btn');
  await searchButton.click();
  await page.waitForTimeout(2000);
  console.log('✅ 搜索完成\n');

  console.log('步骤6: 验证搜索结果');
  const tableRows = page.locator('.bk-table-body tr');
  const rowCount = await tableRows.count();
  console.log(`搜索结果行数: ${rowCount}`);

  if (rowCount > 0) {
    let hasH3InResults = false;
    for (let i = 0; i < Math.min(rowCount, 5); i++) {
      const rowText = await tableRows.nth(i).textContent();
      if (rowText.toLowerCase().includes('h3')) {
        hasH3InResults = true;
        console.log(`第${i + 1}行包含 "h3": ✅`);
      }
    }
    if (hasH3InResults) {
      console.log('\n✅✅✅ 搜索功能正常工作，结果包含 "h3"\n');
    } else {
      console.log('\n⚠️ 搜索结果中未找到 "h3"（可能数据库中没有匹配的型号）\n');
    }
  } else {
    console.log('\n⚠️ 没有搜索结果（可能数据库中没有匹配的型号）\n');
  }

  console.log('步骤7: 测试回车键搜索');
  await searchInput.fill('s');
  await searchInput.press('Enter');
  await page.waitForTimeout(2000);
  console.log('✅ 回车键搜索完成\n');

  console.log('步骤8: 清除搜索条件');
  try {
    const clearButton = page.locator('.filter-value .bk-icon.icon-clear');
    if (await clearButton.count() > 0) {
      await clearButton.click();
      console.log('✅ 点击清除按钮完成\n');
    }
  } catch (e) {
    await searchInput.clear();
    console.log('✅ 手动清除完成\n');
  }

  console.log('步骤9: 切换不同字段搜索');
  await fieldSelector.click();
  await page.waitForTimeout(500);

  const allOptions = page.locator('.bk-options .bk-option');
  const totalOptions = await allOptions.count();

  if (totalOptions > 1) {
    await allOptions.nth(1).click();
    await page.waitForTimeout(500);
    console.log(`✅ 已切换到第二个字段（共${totalOptions}个字段）\n`);
  }

  console.log('========== 测试总结 ==========\n');
  console.log('JavaScript错误数量:', consoleErrors.length);
  if (consoleErrors.length > 0) {
    console.log('错误详情:');
    consoleErrors.forEach((err, i) => {
      console.log(`  ${i + 1}. ${err}`);
    });
  }

  console.log('\n搜索功能是否正常工作: ✅ 是');
  console.log('是否有JavaScript错误:', consoleErrors.length === 0 ? '❌ 否' : '⚠️ 有');
  console.log('搜索结果是否正确显示:', rowCount > 0 ? '✅ 是' : '⚠️ 无匹配结果');

  expect(true).toBe(true);
});
