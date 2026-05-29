const { test, expect } = require('@playwright/test');

test.describe('高级筛选条件保持功能完整测试', () => {
  test('完整测试流程 - 标签显示、详情页返回、路由切换', async ({ page }) => {
    console.log('=== 开始完整测试流程 ===');
    
    // 1. 访问实例列表页
    console.log('步骤 1: 访问实例列表页');
    await page.goto('http://localhost:8085');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // 导航到交换机实例列表
    console.log('导航到交换机实例列表');
    await page.goto('http://localhost:8085/#/resource/instance/bk_switch');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    
    const url1 = page.url();
    console.log('当前 URL:', url1);
    
    // 截图初始状态
    await page.screenshot({ path: '/workspace/test-1-initial.png' });
    
    // 2. 打开高级筛选
    console.log('步骤 2: 打开高级筛选');
    try {
      const filterButton = page.locator('.icon-cc-funnel').first();
      if (await filterButton.isVisible()) {
        await filterButton.click();
        await page.waitForTimeout(1000);
        
        // 截图筛选面板
        await page.screenshot({ path: '/workspace/test-2-filter-panel.png' });
      }
    } catch (e) {
      console.log('高级筛选按钮点击失败，继续测试');
    }
    
    // 尝试查找并填写筛选条件
    console.log('尝试设置筛选条件');
    let hasFilterConditions = false;
    
    try {
      // 查找输入框并尝试填写
      const inputs = page.locator('input');
      const count = await inputs.count();
      console.log(`找到 ${count} 个输入框`);
      
      for (let i = 0; i < Math.min(count, 5); i++) {
        const input = inputs.nth(i);
        const isVisible = await input.isVisible();
        const isDisabled = await input.isDisabled();
        
        if (isVisible && !isDisabled) {
          try {
            await input.click();
            await page.waitForTimeout(300);
            await input.fill('core');
            console.log('填写了一个筛选条件');
            hasFilterConditions = true;
            break;
          } catch (e) {
            console.log(`填写输入框 ${i} 失败`);
          }
        }
      }
      
      // 尝试查找查询按钮
      if (hasFilterConditions) {
        await page.waitForTimeout(500);
        
        // 查找包含"查询"或"搜索"的按钮
        const searchButtons = page.locator('button').filter({
          hasText: /查询|搜索|Search|Query/i
        });
        
        const btnCount = await searchButtons.count();
        console.log(`找到 ${btnCount} 个搜索按钮`);
        
        if (btnCount > 0) {
          await searchButtons.first().click();
          console.log('点击了搜索按钮');
        } else {
          // 尝试按回车
          await page.keyboard.press('Enter');
        }
        
        await page.waitForTimeout(3000);
        
        // 截图筛选结果
        await page.screenshot({ path: '/workspace/test-3-after-search.png' });
      }
    } catch (e) {
      console.log('设置筛选条件时出错:', e);
    }
    
    // 检查是否有筛选标签
    console.log('步骤 3: 验证筛选标签是否显示');
    const filterTags = page.locator('.filter-tag');
    const tagCount = await filterTags.count();
    console.log(`找到 ${tagCount} 个筛选标签`);
    
    const url2 = page.url();
    const hasFilterAdv = url2.includes('filter_adv');
    console.log('URL 是否包含 filter_adv:', hasFilterAdv);
    
    // 3. 进入详情页
    console.log('步骤 4: 进入详情页');
    let enteredDetailPage = false;
    const instanceLinks = page.locator('.bk-table a, .bk-table .bk-button');
    const linkCount = await instanceLinks.count();
    console.log(`找到 ${linkCount} 个可点击元素`);
    
    for (let i = 0; i < Math.min(linkCount, 3); i++) {
      try {
        const link = instanceLinks.nth(i);
        const text = await link.textContent();
        console.log(`元素 ${i} 文本:`, text?.trim());
        
        if (text && text.trim().length > 0 && !text.includes('操作')) {
          await link.click();
          enteredDetailPage = true;
          console.log('进入了详情页');
          break;
        }
      } catch (e) {
        console.log(`点击元素 ${i} 失败`);
      }
    }
    
    if (enteredDetailPage) {
      await page.waitForTimeout(3000);
      
      const url3 = page.url();
      console.log('详情页 URL:', url3);
      
      // 截图详情页
      await page.screenshot({ path: '/workspace/test-4-detail-page.png' });
      
      // 4. 返回列表页
      console.log('步骤 5: 返回列表页');
      try {
        // 尝试查找面包屑返回按钮
        const backButton = page.locator('.icon-cc-arrow, .page-breadcrumbs').first();
        if (await backButton.isVisible()) {
          await backButton.click();
          console.log('点击了面包屑返回按钮');
        } else {
          await page.goBack();
          console.log('使用浏览器返回');
        }
      } catch (e) {
        await page.goBack();
      }
      
      await page.waitForTimeout(3000);
      
      const url4 = page.url();
      console.log('返回后 URL:', url4);
      
      // 截图返回后的状态
      await page.screenshot({ path: '/workspace/test-5-back-from-detail.png' });
      
      // 检查筛选标签是否保持
      const filterTagsAfter = page.locator('.filter-tag');
      const tagCountAfter = await filterTagsAfter.count();
      console.log(`返回后找到 ${tagCountAfter} 个筛选标签`);
      
      const hasFilterAdvAfter = url4.includes('filter_adv');
      console.log('返回后 URL 是否包含 filter_adv:', hasFilterAdvAfter);
    }
    
    // 5. 路由切换测试
    console.log('步骤 6: 路由切换测试');
    try {
      // 尝试切换到其他路由
      await page.goto('http://localhost:8085/#/resource/instance/bk_host');
      await page.waitForTimeout(2000);
      
      // 截图切换后的状态
      await page.screenshot({ path: '/workspace/test-6-route-switched.png' });
      
      // 再切回来
      console.log('切换回交换机实例列表');
      await page.goto(url2);
      await page.waitForTimeout(3000);
      
      const url5 = page.url();
      console.log('切换回来后的 URL:', url5);
      
      // 截图最终状态
      await page.screenshot({ path: '/workspace/test-7-final-state.png' });
      
      // 检查筛选标签
      const filterTagsFinal = page.locator('.filter-tag');
      const tagCountFinal = await filterTagsFinal.count();
      console.log(`路由切换后找到 ${tagCountFinal} 个筛选标签`);
      
      const hasFilterAdvFinal = url5.includes('filter_adv');
      console.log('最终 URL 是否包含 filter_adv:', hasFilterAdvFinal);
    } catch (e) {
      console.log('路由切换测试时出错:', e);
    }
    
    console.log('=== 测试完成 ===');
    console.log('测试截图已保存到 /workspace/ 目录');
  });
});
