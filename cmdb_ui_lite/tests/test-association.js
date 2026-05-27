const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const testResults = {
    success: true,
    steps: [],
    errors: []
  };

  try {
    console.log('=== SLB实例详情页关联Tab功能测试 ===\n');

    console.log('步骤1: 访问 http://localhost:3000');
    await page.goto('http://localhost:3000/', { waitUntil: 'networkidle', timeout: 30000 });
    testResults.steps.push({ name: '访问首页', status: 'pass' });
    console.log('✅ 页面加载成功\n');

    console.log('步骤2: 进入资源管理页面');
    await page.waitForSelector('text=资源', { timeout: 5000 });
    await page.click('text=资源');
    await page.waitForTimeout(1000);
    testResults.steps.push({ name: '进入资源管理页面', status: 'pass' });
    console.log('✅ 资源管理页面加载成功\n');

    console.log('步骤3: 选择"负载均衡"模型');
    await page.waitForSelector('text=负载均衡', { timeout: 5000 });
    await page.click('text=负载均衡');
    await page.waitForTimeout(1000);
    testResults.steps.push({ name: '选择负载均衡模型', status: 'pass' });
    console.log('✅ 负载均衡模型选择成功\n');

    console.log('步骤4: 点击SLB实例"web-slb-public"进入详情页');
    await page.waitForSelector('text=web-slb-public', { timeout: 5000 });
    await page.click('text=web-slb-public');
    await page.waitForTimeout(1500);
    testResults.steps.push({ name: '点击SLB实例进入详情页', status: 'pass' });
    console.log('✅ 进入详情页成功\n');

    console.log('步骤5: 切换到"关联"Tab');
    const associationTab = page.locator('.bk-tab-label-item, [role="tab"]').filter({ hasText: '关联' });
    const tabCount = await associationTab.count();

    console.log(`   找到 ${tabCount} 个"关联"Tab元素`);

    if (tabCount === 0) {
      testResults.errors.push('未找到"关联"Tab');
      testResults.success = false;
      console.log('❌ 未找到"关联"Tab\n');

      const pageText = await page.textContent('body');
      console.log('页面内容检查:');
      console.log('   包含"基本信息":', pageText.includes('基本信息'));
      console.log('   包含"关联":', pageText.includes('关联'));
    } else {
      await associationTab.first().click();
      await page.waitForTimeout(1000);
      testResults.steps.push({ name: '切换到关联Tab', status: 'pass' });
      console.log('✅ 切换到关联Tab成功\n');

      console.log('步骤6: 验证关联数据');
      await page.waitForTimeout(1500);

      const pageText = await page.textContent('body');

      const hasSlbServer = pageText.includes('SLB后端服务器');
      const hasSlbListener = pageText.includes('SLB监听器');
      const hasEmptyState = pageText.includes('暂无关联关系');

      console.log('   关联Tab是否可见:', !hasEmptyState ? '是' : '否');
      console.log('   包含"SLB后端服务器":', hasSlbServer ? '是' : '否');
      console.log('   包含"SLB监听器":', hasSlbListener ? '是' : '否');
      console.log('   显示"暂无关联关系":', hasEmptyState ? '是' : '否');

      const associationGroups = await page.$$('.association-group');
      console.log(`\n   发现 ${associationGroups.length} 个关联组`);

      const groupDetails = [];
      for (let i = 0; i < associationGroups.length; i++) {
        const group = associationGroups[i];
        const titleElement = await group.$('.title-text');
        const countElement = await group.$('.title-count');

        if (titleElement && countElement) {
          const title = await titleElement.textContent();
          const count = await countElement.textContent();
          groupDetails.push({ title: title.trim(), count: count.trim() });
          console.log(`   关联组 ${i + 1}: ${title.trim()} ${count.trim()}`);
        }

        const tableRows = await group.$$('tbody tr');
        console.log(`      包含 ${tableRows.length} 个实例`);
      }

      testResults.associationDetails = {
        hasAssociationTab: !hasEmptyState,
        associationGroups: groupDetails,
        hasSlbServer,
        hasSlbListener,
        hasEmptyState
      };

      if (hasSlbServer && hasSlbListener && !hasEmptyState) {
        testResults.steps.push({ name: '验证关联数据', status: 'pass' });
        console.log('\n✅ 关联数据验证成功');
      } else {
        testResults.errors.push('关联数据验证失败');
        testResults.success = false;
        console.log('\n❌ 关联数据验证失败');
      }
    }

    console.log('\n=== 测试总结 ===');
    console.log(`总步骤数: ${testResults.steps.length}`);
    console.log(`成功步骤: ${testResults.steps.filter(s => s.status === 'pass').length}`);
    console.log(`失败步骤: ${testResults.steps.filter(s => s.status === 'fail').length}`);
    console.log(`错误数: ${testResults.errors.length}`);

    if (testResults.errors.length > 0) {
      console.log('\n错误详情:');
      testResults.errors.forEach(err => console.log(`  - ${err}`));
    }

    console.log('\n=== 最终结果 ===');
    if (testResults.success) {
      console.log('✅ 所有测试通过');
    } else {
      console.log('❌ 测试存在失败项');
    }

    const screenshotPath = '/workspace/bk-cmdb/cmdb_ui_lite/test-result-screenshot.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`\n截图已保存: ${screenshotPath}`);

    console.log('\n=== 详细测试报告 ===');
    console.log(JSON.stringify(testResults, null, 2));

  } catch (error) {
    console.error('\n❌ 测试执行出错:', error.message);
    testResults.errors.push(error.message);
    testResults.success = false;

    try {
      await page.screenshot({ path: '/workspace/bk-cmdb/cmdb_ui_lite/test-error-screenshot.png' });
      console.log('错误截图已保存: /workspace/bk-cmdb/cmdb_ui_lite/test-error-screenshot.png');
    } catch (e) {
      console.log('无法保存截图');
    }

    console.log('\n=== 错误后的测试报告 ===');
    console.log(JSON.stringify(testResults, null, 2));
  } finally {
    await browser.close();
  }

  process.exit(testResults.success ? 0 : 1);
})();
