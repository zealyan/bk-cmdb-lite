/**
 * 面包屑导航返回测试脚本
 * 测试场景：
 * 1. 在实例列表页设置高级筛选条件
 * 2. 点击实例进入详情页
 * 3. 点击面包屑返回按钮
 * 4. 验证高级筛选条件是否被保留
 */

const { test, expect } = require('@playwright/test');

test('面包屑返回时高级筛选条件保持', async ({ page }) => {
  console.log('开始测试：面包屑返回时高级筛选条件保持');
  
  // 1. 访问实例列表页（交换机）
  await page.goto('http://localhost:8080/#/resource/instance/bk_switch');
  await page.waitForLoadState('networkidle');
  console.log('步骤1: 访问实例列表页');
  
  // 2. 等待页面加载完成
  await page.waitForTimeout(2000);
  
  // 3. 记录初始 URL
  const initialUrl = page.url();
  console.log('初始 URL:', initialUrl);
  
  // 4. 点击高级筛选按钮
  const filterButton = page.locator('.icon-cc-funnel');
  await filterButton.click();
  console.log('步骤2: 点击高级筛选按钮');
  
  // 5. 等待高级筛选弹窗打开
  await page.waitForTimeout(500);
  
  // 6. 设置一个筛选条件（例如选择厂商不为空的交换机）
  const conditionInput = page.locator('.general-model-filter .bk-input input').first();
  if (await conditionInput.isVisible()) {
    await conditionInput.fill('Cisco');
    console.log('步骤3: 输入筛选条件');
  }
  
  // 7. 点击搜索按钮
  const searchButton = page.locator('.general-model-filter .bk-button.primary').first();
  if (await searchButton.isVisible()) {
    await searchButton.click();
    console.log('步骤4: 点击搜索按钮');
  }
  
  // 8. 等待搜索结果加载
  await page.waitForTimeout(2000);
  
  // 9. 检查 URL 是否包含 filter_adv 参数
  const urlAfterFilter = page.url();
  console.log('筛选后 URL:', urlAfterFilter);
  
  // 10. 检查是否有 filter_adv 参数
  const hasFilterAdv = urlAfterFilter.includes('filter_adv=');
  console.log('URL 是否包含 filter_adv:', hasFilterAdv);
  
  if (!hasFilterAdv) {
    console.log('警告: URL 中没有 filter_adv 参数');
    // 继续测试，即使没有参数也要尝试返回
  }
  
  // 11. 点击第一个实例进入详情页
  const firstInstanceLink = page.locator('.bk-table tbody tr:first-child .bk-button.text').first();
  if (await firstInstanceLink.isVisible()) {
    await firstInstanceLink.click();
    console.log('步骤5: 点击实例进入详情页');
  }
  
  // 12. 等待详情页加载
  await page.waitForTimeout(2000);
  
  // 13. 检查详情页 URL
  const urlAfterNavigate = page.url();
  console.log('详情页 URL:', urlAfterNavigate);
  
  // 14. 检查详情页 URL 是否包含 filter_adv 参数
  const hasFilterAdvInDetails = urlAfterNavigate.includes('filter_adv=');
  console.log('详情页 URL 是否包含 filter_adv:', hasFilterAdvInDetails);
  
  // 15. 点击返回按钮（面包屑）
  const backButton = page.locator('.page-breadcrumbs .icon');
  if (await backButton.isVisible()) {
    await backButton.click();
    console.log('步骤6: 点击返回按钮');
  } else {
    // 尝试使用浏览器返回
    await page.goBack();
    console.log('步骤6: 使用浏览器返回');
  }
  
  // 16. 等待列表页加载
  await page.waitForTimeout(2000);
  
  // 17. 检查返回后 URL 是否包含 filter_adv 参数
  const urlAfterBack = page.url();
  console.log('返回后 URL:', urlAfterBack);
  
  // 18. 检查高级筛选标签是否显示
  const filterTags = page.locator('.filter-tag');
  const hasFilterTags = await filterTags.isVisible();
  console.log('是否有筛选标签:', hasFilterTags);
  
  // 19. 验证结果
  const hasFilterAdvAfterBack = urlAfterBack.includes('filter_adv=');
  
  console.log('===== 测试结果 =====');
  console.log('1. 初始 URL:', initialUrl);
  console.log('2. 筛选后 URL:', urlAfterFilter);
  console.log('3. 详情页 URL:', urlAfterNavigate);
  console.log('4. 返回后 URL:', urlAfterBack);
  console.log('5. 返回后包含 filter_adv:', hasFilterAdvAfterBack);
  console.log('6. 显示筛选标签:', hasFilterTags);
  
  // 验证：如果返回后 URL 包含 filter_adv 参数，说明测试通过
  if (hasFilterAdvAfterBack) {
    console.log('✅ 测试通过: 面包屑返回时高级筛选条件已保持');
  } else {
    console.log('❌ 测试失败: 面包屑返回时高级筛选条件丢失');
    // 抛出错误以便测试失败
    throw new Error('面包屑返回时高级筛选条件丢失');
  }
});
