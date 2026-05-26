const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const testResults = {
    testName: 'SLB实例详情页关联Tab功能测试',
    timestamp: new Date().toISOString(),
    steps: [],
    results: {
      associationTabVisible: false,
      associationGroupCount: 0,
      associationGroups: [],
      hasSlbServer: false,
      hasSlbListener: false,
      hasEmptyState: false,
      totalInstancesCount: 0
    },
    errors: [],
    success: true
  };

  try {
    console.log('=== SLB实例详情页关联Tab功能完整测试 ===\n');

    console.log('步骤1: 访问 http://localhost:3000');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    testResults.steps.push({ name: '访问首页', status: 'pass' });
    console.log('✅ 页面加载成功\n');

    console.log('步骤2: 进入资源管理页面');
    await page.click('text=资源');
    await page.waitForTimeout(2000);
    testResults.steps.push({ name: '进入资源管理页面', status: 'pass' });
    console.log('✅ 资源管理页面加载成功\n');

    console.log('步骤3: 选择"负载均衡"模型');
    await page.click('text=负载均衡');
    await page.waitForTimeout(2000);
    testResults.steps.push({ name: '选择负载均衡模型', status: 'pass' });
    console.log('✅ 负载均衡模型选择成功\n');

    console.log('步骤4: 点击SLB实例"web-slb-public"进入详情页');
    await page.waitForTimeout(500);
    await page.click('text=1');
    await page.waitForTimeout(2000);
    testResults.steps.push({ name: '点击SLB实例进入详情页', status: 'pass' });
    console.log('✅ 进入详情页成功\n');

    console.log('步骤5: 切换到"关联"Tab');
    const associationTab = page.locator('[role="tab"], .bk-tab-label-item').filter({ hasText: '关联' });
    await associationTab.first().click();
    await page.waitForTimeout(2000);
    testResults.steps.push({ name: '切换到关联Tab', status: 'pass' });
    console.log('✅ 切换到关联Tab成功\n');

    console.log('步骤6: 验证关联数据');
    const bodyText = await page.textContent('body');

    testResults.results.hasSlbServer = bodyText.includes('SLB后端服务器');
    testResults.results.hasSlbListener = bodyText.includes('SLB监听器');
    testResults.results.hasEmptyState = bodyText.includes('暂无关联关系');
    testResults.results.associationTabVisible = !testResults.results.hasEmptyState;

    console.log('  关联Tab可见:', testResults.results.associationTabVisible ? '✅ 是' : '❌ 否');
    console.log('  包含"SLB后端服务器":', testResults.results.hasSlbServer ? '✅ 是' : '❌ 否');
    console.log('  包含"SLB监听器":', testResults.results.hasSlbListener ? '✅ 是' : '❌ 否');
    console.log('  显示"暂无关联关系":', testResults.results.hasEmptyState ? '❌ 是' : '✅ 否');

    const groups = await page.locator('.association-group').all();
    testResults.results.associationGroupCount = groups.length;
    console.log(`\n  关联组数量: ${groups.length}`);

    let totalInstances = 0;
    for (let i = 0; i < groups.length; i++) {
      const groupText = await groups[i].textContent();

      // 提取关联组名称
      const titleMatch = groupText.match(/^(.*?)(\(\d+\))/);
      const groupName = titleMatch ? titleMatch[1].trim() : `关联组 ${i + 1}`;
      const countMatch = groupText.match(/\((\d+)\)/);
      const count = countMatch ? parseInt(countMatch[1]) : 0;

      totalInstances += count;

      testResults.results.associationGroups.push({
        name: groupName,
        instanceCount: count,
        hasInstances: count > 0
      });

      console.log(`\n  关联组 ${i + 1}: ${groupName}`);
      console.log(`    实例数量: ${count}`);
      console.log(`    有实例数据: ${count > 0 ? '✅ 是' : '❌ 否'}`);
    }

    testResults.results.totalInstancesCount = totalInstances;
    console.log(`\n  总关联实例数: ${totalInstances}`);

    // 验证预期结果
    console.log('\n=== 预期结果验证 ===');

    const check1 = testResults.results.associationTabVisible;
    const check2 = testResults.results.associationGroupCount >= 2;
    const check3 = testResults.results.hasSlbServer;
    const check4 = testResults.results.hasSlbListener;
    const check5 = !testResults.results.hasEmptyState;
    const check6 = testResults.results.totalInstancesCount >= 3;

    console.log(`  1. 关联Tab可见: ${check1 ? '✅ 通过' : '❌ 未通过'}`);
    console.log(`  2. 至少2个关联组: ${check2 ? '✅ 通过' : '❌ 未通过'} (实际: ${testResults.results.associationGroupCount})`);
    console.log(`  3. 包含"SLB后端服务器": ${check3 ? '✅ 通过' : '❌ 未通过'}`);
    console.log(`  4. 包含"SLB监听器": ${check4 ? '✅ 通过' : '❌ 未通过'}`);
    console.log(`  5. 不是"暂无关联关系": ${check5 ? '✅ 通过' : '❌ 未通过'}`);
    console.log(`  6. 有关联实例数据: ${check6 ? '✅ 通过' : '❌ 未通过'} (实际: ${testResults.results.totalInstancesCount}个)`);

    testResults.success = check1 && check2 && check3 && check4 && check5 && check6;

    console.log('\n=== 测试总结 ===');
    console.log(`总步骤数: ${testResults.steps.length}`);
    console.log(`成功步骤: ${testResults.steps.filter(s => s.status === 'pass').length}`);
    console.log(`关联组数量: ${testResults.results.associationGroupCount}`);
    console.log(`关联实例总数: ${testResults.results.totalInstancesCount}`);

    if (testResults.errors.length > 0) {
      console.log('\n错误详情:');
      testResults.errors.forEach(err => console.log(`  - ${err}`));
    }

    console.log('\n=== 最终结果 ===');
    if (testResults.success) {
      console.log('✅ 所有测试通过 - 关联Tab功能正常');
    } else {
      console.log('❌ 测试存在失败项');
    }

    const screenshotPath = '/workspace/bk-cmdb/cmdb_ui_lite/test-association-complete.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`\n截图已保存: ${screenshotPath}`);

    console.log('\n=== JSON格式测试报告 ===');
    console.log(JSON.stringify(testResults, null, 2));

  } catch (error) {
    console.error('\n❌ 测试执行出错:', error.message);
    testResults.errors.push(error.message);
    testResults.success = false;

    try {
      await page.screenshot({ path: '/workspace/bk-cmdb/cmdb_ui_lite/test-error-final.png' });
      console.log('错误截图已保存');
    } catch (e) {
      console.log('无法保存截图');
    }
  } finally {
    await browser.close();
  }

  process.exit(testResults.success ? 0 : 1);
})();
