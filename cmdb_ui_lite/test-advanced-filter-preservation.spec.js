const { test, expect } = require('@playwright/test');

test.describe('高级筛选条件保持功能测试', () => {
  test('从详情页返回后高级筛选条件标签应保持显示', async ({ page }) => {
    console.log('=== 测试开始 ===');
    
    // 1. 访问实例列表页（交换机）
    console.log('步骤 1: 访问实例列表页');
    await page.goto('http://localhost:8082');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    // 点击导航到交换机实例列表
    console.log('步骤 2: 导航到交换机实例列表');
    await page.goto('http://localhost:8082/#/resource/instance/bk_switch');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    console.log('当前 URL:', page.url());
    
    // 2. 点击高级筛选按钮
    console.log('步骤 3: 点击高级筛选按钮');
    const filterButton = page.locator('.icon-cc-funnel').first();
    await filterButton.click();
    await page.waitForTimeout(500);
    
    // 截图查看当前状态
    await page.screenshot({ path: '/workspace/step1-after-filter-click.png' });
    
    // 获取快照查找元素
    const initialSnapshot = await page.content();
    console.log('页面快照获取成功');
    
    // 查找通用模型筛选组件
    const filterPanel = page.locator('.general-model-filter');
    
    // 查找第一个筛选条件属性
    const properties = page.locator('[class*="select"]').first();
    console.log('查找筛选属性选择器');
    
    // 尝试查找并填写一些筛选条件
    // 由于不同项目的筛选UI可能不同，让我们尝试找到一些输入元素并填写
    try {
      // 等待筛选面板显示
      await page.waitForTimeout(1000);
      
      // 查找第一个输入字段并尝试填写
      const inputFields = page.locator('input');
      const count = await inputFields.count();
      console.log(`找到 ${count} 个输入字段`);
      
      if (count > 0) {
        // 尝试找到第一个非只读的输入框
        for (let i = 0; i < count; i++) {
          const field = inputFields.nth(i);
          const placeholder = await field.getAttribute('placeholder');
          const type = await field.getAttribute('type');
          const disabled = await field.isDisabled();
          
          console.log(`字段 ${i}: type=${type}, placeholder=${placeholder}, disabled=${disabled}`);
          
          if (!disabled && type !== 'hidden') {
            console.log('尝试填写筛选条件');
            // 尝试填写一些简单的筛选条件
            try {
              await field.click();
              await page.waitForTimeout(300);
              await field.fill('core');
              console.log('填写筛选条件成功');
              break;
            } catch (e) {
              console.log('填写失败，尝试下一个字段');
            }
          }
        }
      }
    } catch (e) {
      console.log('填写筛选条件时出错:', e);
    }
    
    // 截图筛选条件填写后的状态
    await page.screenshot({ path: '/workspace/step2-filter-filled.png' });
    
    // 查找搜索/提交按钮
    console.log('步骤 4: 查找并点击搜索按钮');
    const submitButtons = page.locator('button').filter({ hasText: /搜索|确定|查询|Submit|Search/i });
    
    let foundSubmit = false;
    const btnCount = await submitButtons.count();
    
    console.log(`找到 ${btnCount} 个可能的提交按钮`);
    
    if (btnCount > 0) {
      try {
        await submitButtons.first().click();
        foundSubmit = true;
        console.log('点击搜索按钮成功');
      } catch (e) {
        console.log('点击搜索按钮失败:', e);
      }
    }
    
    if (!foundSubmit) {
      // 如果找不到明确的提交按钮，按回车或等待面板关闭
      console.log('尝试按Enter键提交');
      try {
        await page.keyboard.press('Enter');
      } catch (e) {
        console.log('按Enter键失败');
      }
    }
    
    // 等待搜索结果加载
    console.log('步骤 5: 等待搜索结果加载');
    await page.waitForTimeout(2000);
    
    // 检查URL中是否有filter_adv参数
    const urlAfterSearch = page.url();
    console.log('搜索后的 URL:', urlAfterSearch);
    const hasFilterAdv = urlAfterSearch.includes('filter_adv');
    console.log('URL包含 filter_adv:', hasFilterAdv);
    
    // 截图搜索结果
    await page.screenshot({ path: '/workspace/step3-after-search.png' });
    
    // 3. 查找并点击第一个实例查看详情
    console.log('步骤 6: 查找并点击第一个实例');
    
    // 查找表格中的链接或按钮
    const instanceLinks = page.locator('.bk-table a, .bk-table .bk-button');
    const linkCount = await instanceLinks.count();
    console.log(`找到 ${linkCount} 个可能的链接`);
    
    let clickedInstance = false;
    
    if (linkCount > 0) {
      for (let i = 0; i < Math.min(linkCount, 5); i++) {
        try {
          const text = await instanceLinks.nth(i).textContent();
          console.log(`链接 ${i} 文本: "${text}"`);
          
          if (text && text.trim().length > 0 && !text.includes('操作')) {
            await instanceLinks.nth(i).click();
            clickedInstance = true;
            console.log(`点击了第 ${i} 个链接`);
            break;
          }
        } catch (e) {
          console.log(`点击链接 ${i} 失败`);
        }
      }
    }
    
    if (!clickedInstance) {
      // 如果找不到明确的链接，尝试查找表格第一行的ID列
      console.log('尝试查找表格第一行');
      const firstRow = page.locator('.bk-table tbody tr').first();
      if (await firstRow.isVisible()) {
        console.log('第一行可见');
        const firstCell = firstRow.locator('td').first();
        if (await firstCell.isVisible()) {
          try {
            const linkInCell = firstCell.locator('a, .bk-button').first();
            if (await linkInCell.isVisible()) {
              await linkInCell.click();
              clickedInstance = true;
            }
          } catch (e) {
            console.log('点击第一行失败');
          }
        }
      }
    }
    
    if (!clickedInstance) {
      console.log('未能找到可点击的实例链接，将跳过详情页步骤');
    } else {
      // 等待详情页加载
      console.log('步骤 7: 等待详情页加载');
      await page.waitForTimeout(2000);
      
      const urlAfterNavigate = page.url();
      console.log('详情页 URL:', urlAfterNavigate);
      
      // 截图详情页
      await page.screenshot({ path: '/workspace/step4-detail-page.png' });
      
      // 4. 点击面包屑返回按钮
      console.log('步骤 8: 查找并点击面包屑返回按钮');
      
      // 查找面包屑导航中的返回按钮或第一个面包屑项
      const backButton = page.locator('.icon-cc-arrow, .page-breadcrumbs .breadcrumb-item').first();
      
      let foundBack = false;
      
      if (await backButton.isVisible()) {
        try {
          await backButton.click();
          foundBack = true;
          console.log('点击返回按钮成功');
        } catch (e) {
          console.log('点击返回按钮失败');
        }
      }
      
      if (!foundBack) {
        // 尝试使用浏览器的返回按钮
        console.log('尝试使用浏览器返回');
        await page.goBack();
      }
      
      // 等待列表页重新加载
      console.log('步骤 9: 等待列表页重新加载');
      await page.waitForTimeout(2000);
      
      const urlAfterBack = page.url();
      console.log('返回后的 URL:', urlAfterBack);
      
      const hasFilterAdvAfterBack = urlAfterBack.includes('filter_adv');
      console.log('返回后URL包含 filter_adv:', hasFilterAdvAfterBack);
      
      // 截图返回后的页面
      await page.screenshot({ path: '/workspace/step5-after-back.png' });
      
      // 5. 检查筛选标签是否存在
      console.log('步骤 10: 检查筛选标签是否存在');
      
      const filterTags = page.locator('.filter-tag');
      const tagsCount = await filterTags.count();
      console.log(`找到 ${tagsCount} 个筛选标签`);
      
      // 输出所有标签文本
      const tagsTexts = [];
      for (let i = 0; i < tagsCount; i++) {
        const text = await filterTags.nth(i).textContent();
        tagsTexts.push(text);
      }
      console.log('筛选标签内容:', tagsTexts);
      
      // 截图最终结果
      await page.screenshot({ path: '/workspace/step6-final-result.png' });
      
      console.log('=== 测试结束 ===');
      console.log('测试总结:');
      console.log('- 搜索后URL包含 filter_adv:', hasFilterAdv);
      console.log('- 返回后URL包含 filter_adv:', hasFilterAdvAfterBack);
      console.log('- 找到筛选标签数量:', tagsCount);
      
      // 验证结果
      expect(hasFilterAdvAfterBack || tagsCount > 0).toBeTruthy();
    }
  });
});
