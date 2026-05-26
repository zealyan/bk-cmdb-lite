const { test, expect } = require('@playwright/test');

test('交换机列表-所属业务字段搜索功能测试', async ({ page }) => {
  const consoleMessages = [];
  const consoleErrors = [];
  const networkErrors = [];
  
  // 监听控制台消息
  page.on('console', msg => {
    const text = msg.text();
    consoleMessages.push({ type: msg.type(), text });
    if (msg.type() === 'error') {
      consoleErrors.push(text);
      console.log(`[控制台错误] ${text}`);
    }
  });
  
  // 监听页面错误
  page.on('pageerror', error => {
    consoleErrors.push(`页面错误: ${error.message}`);
    console.log(`[页面错误] ${error.message}`);
  });
  
  // 监听网络错误
  page.on('requestfailed', request => {
    networkErrors.push(`${request.url()} - ${request.failure().errorText}`);
    console.log(`[网络错误] ${request.url()} - ${request.failure().errorText}`);
  });

  try {
    // Step 1: 访问首页
    console.log('\n=== Step 1: 访问首页 ===');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);
    console.log('✓ 页面加载完成');
    
    // Step 2: 直接导航到交换机列表
    console.log('\n=== Step 2: 导航到交换机列表 ===');
    await page.goto('http://localhost:3000/#/instance/bk_switch', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    console.log('✓ 交换机列表页面加载完成');
    
    // Step 3: 查找并点击字段选择器
    console.log('\n=== Step 3: 选择"所属业务"字段 ===');
    await page.waitForTimeout(1000);
    
    // 查找搜索字段选择器
    const fieldSelector = await page.locator('.search-field-selector, .bk-select, .bk-dropdown, [class*="search"] [class*="select"]').first();
    const isVisible = await fieldSelector.isVisible().catch(() => false);
    
    if (!isVisible) {
      // 尝试查找所有可能的搜索控件
      const allSelectors = await page.locator('[class*="search"], [class*="field"], [class*="select"]').all();
      console.log(`找到 ${allSelectors.length} 个可能的搜索相关元素`);
      
      // 查找包含"字段"或"field"文字的元素
      const fieldLabel = page.locator('text=/字段|field/i');
      if (await fieldLabel.count() > 0) {
        console.log('✓ 找到字段选择器标签');
        await fieldLabel.first().click();
        await page.waitForTimeout(500);
      }
    } else {
      await fieldSelector.click();
      await page.waitForTimeout(500);
      console.log('✓ 点击了字段选择器');
    }
    
    // Step 4: 在下拉列表中选择"所属业务"
    console.log('\n=== Step 4: 选择"所属业务"选项 ===');
    await page.waitForTimeout(500);
    
    const businessOption = page.locator('text=/所属业务|business/i');
    const hasBusinessOption = await businessOption.count() > 0;
    
    if (hasBusinessOption) {
      await businessOption.first().click();
      console.log('✓ 已选择"所属业务"字段');
      await page.waitForTimeout(1000);
    } else {
      console.log('⚠ 未找到"所属业务"选项，尝试其他方式...');
      // 列出所有可见的选项
      const allOptions = await page.locator('.bk-select-option, .bk-dropdown-item, [class*="option"]').allTextContents();
      console.log('可用选项:', allOptions.slice(0, 10));
    }
    
    // Step 5: 输入"游戏"进行搜索
    console.log('\n=== Step 5: 输入"游戏"进行搜索 ===');
    await page.waitForTimeout(500);
    
    const searchInput = await page.locator('input[type="text"], input[class*="search"], input[class*="input"]').last();
    const inputVisible = await searchInput.isVisible().catch(() => false);
    
    if (inputVisible) {
      await searchInput.fill('游戏');
      console.log('✓ 已在搜索框输入"游戏"');
      await page.waitForTimeout(1000);
      
      // 检查输入后是否有错误
      if (consoleErrors.length > 0) {
        console.log('\n⚠ 输入后出现错误:');
        consoleErrors.forEach(err => console.log(`  - ${err}`));
      }
    } else {
      console.log('⚠ 未找到搜索输入框');
    }
    
    // Step 6: 点击搜索按钮
    console.log('\n=== Step 6: 点击搜索按钮 ===');
    await page.waitForTimeout(500);
    
    const searchButton = page.locator('button:has-text("搜索"), button[class*="primary"], [class*="search"] button').first();
    const buttonVisible = await searchButton.isVisible().catch(() => false);
    
    if (buttonVisible) {
      await searchButton.click();
      console.log('✓ 已点击搜索按钮');
      await page.waitForTimeout(2000);
      
      // 等待搜索结果
      await page.waitForLoadState('networkidle');
      console.log('✓ 搜索请求完成');
    } else {
      console.log('⚠ 未找到搜索按钮');
    }
    
    // Step 7: 检查搜索结果
    console.log('\n=== Step 7: 检查搜索结果 ===');
    await page.waitForTimeout(1000);
    
    // 尝试查找表格或列表
    const tableRows = await page.locator('table tbody tr, .data-table tbody tr, [class*="table"] tbody tr').count();
    console.log(`找到 ${tableRows} 行数据`);
    
    // 检查是否有错误提示
    const errorAlert = page.locator('[class*="error"], .bk-alert');
    const hasError = await errorAlert.count() > 0;
    
    if (hasError) {
      const errorText = await errorAlert.first().textContent();
      console.log('⚠ 发现错误提示:', errorText);
    }
    
    // Step 8: 总结
    console.log('\n=== 测试总结 ===');
    console.log(`✓ 控制台消息总数: ${consoleMessages.length}`);
    console.log(`✗ 控制台错误数: ${consoleErrors.length}`);
    console.log(`✗ 网络错误数: ${networkErrors.length}`);
    
    if (consoleErrors.length === 0 && networkErrors.length === 0) {
      console.log('\n✓✓✓ 测试通过！没有发现任何JavaScript错误或异常 ✓✓✓');
    } else {
      console.log('\n✗✗✗ 测试发现错误，请查看上方详细信息 ✗✗✗');
    }
    
    // 截图保存
    await page.screenshot({ 
      path: '/workspace/bk-cmdb/cmdb_ui_lite/search-test-result.png', 
      fullPage: true 
    });
    console.log('\n截图已保存: /workspace/bk-cmdb/cmdb_ui_lite/search-test-result.png');
    
    // 期望没有严重错误
    expect(consoleErrors.length).toBe(0);
    
  } catch (error) {
    console.error('\n✗ 测试失败:', error.message);
    await page.screenshot({ 
      path: '/workspace/bk-cmdb/cmdb_ui_lite/search-test-error.png', 
      fullPage: true 
    });
    throw error;
  }
});
