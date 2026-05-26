const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const testResults = {
    success: true,
    steps: [],
    errors: [],
    associations: {
      slbServers: 0,
      slbListeners: 0
    }
  };

  try {
    console.log('='.repeat(60));
    console.log('  SLB ID=1 关联数据修复验证测试');
    console.log('='.repeat(60));
    console.log('\n测试目标:');
    console.log('  - 验证SLB ID=1 (web-slb-public)的关联数据');
    console.log('  - 期望后端服务器: 15条');
    console.log('  - 期望监听器: 15条');
    console.log('='.repeat(60) + '\n');

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

    console.log('步骤4: 点击SLB实例"web-slb-public" (ID=1) 进入详情页');
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
    } else {
      await associationTab.first().click();
      await page.waitForTimeout(1500);
      testResults.steps.push({ name: '切换到关联Tab', status: 'pass' });
      console.log('✅ 切换到关联Tab成功\n');

      console.log('步骤6: 提取并验证关联数据');
      await page.waitForTimeout(1500);

      const associationGroups = await page.$$('.association-group');
      console.log(`   发现 ${associationGroups.length} 个关联组`);

      const groupDetails = [];
      for (let i = 0; i < associationGroups.length; i++) {
        const group = associationGroups[i];
        const titleElement = await group.$('.title-text');
        const countElement = await group.$('.title-count');

        if (titleElement && countElement) {
          const title = await titleElement.textContent();
          const count = await countElement.textContent();
          const cleanTitle = title.trim();
          const cleanCount = count.trim().replace(/[()]/g, '');
          
          groupDetails.push({ title: cleanTitle, count: parseInt(cleanCount) || 0 });
          console.log(`   关联组 ${i + 1}: ${cleanTitle} ${cleanCount}`);

          if (cleanTitle.includes('后端')) {
            testResults.associations.slbServers = parseInt(cleanCount) || 0;
          }
          if (cleanTitle.includes('监听')) {
            testResults.associations.slbListeners = parseInt(cleanCount) || 0;
          }
        }

        const tableRows = await group.$$('tbody tr');
        console.log(`      包含 ${tableRows.length} 个实例`);
      }

      testResults.associationGroups = groupDetails;

      console.log('\n数据验证:');
      console.log(`  后端服务器数量: ${testResults.associations.slbServers} / 期望 15`);
      console.log(`  监听器数量: ${testResults.associations.slbListeners} / 期望 15`);

      const serverCountOk = testResults.associations.slbServers === 15;
      const listenerCountOk = testResults.associations.slbListeners === 15;

      if (serverCountOk && listenerCountOk) {
        testResults.steps.push({ name: '验证关联数据', status: 'pass' });
        console.log('\n✅ 关联数据验证成功！数据完全一致');
      } else {
        testResults.errors.push('关联数据数量不匹配');
        testResults.success = false;
        if (!serverCountOk) {
          console.log(`\n❌ 后端服务器数量不匹配: ${testResults.associations.slbServers} != 15`);
        }
        if (!listenerCountOk) {
          console.log(`\n❌ 监听器数量不匹配: ${testResults.associations.slbListeners} != 15`);
        }
      }
    }

    console.log('\n' + '='.repeat(60));
    console.log('测试总结');
    console.log('='.repeat(60));
    console.log(`总步骤数: ${testResults.steps.length}`);
    console.log(`成功步骤: ${testResults.steps.filter(s => s.status === 'pass').length}`);
    console.log(`失败步骤: ${testResults.steps.filter(s => s.status === 'fail').length}`);
    console.log(`错误数: ${testResults.errors.length}`);

    if (testResults.errors.length > 0) {
      console.log('\n错误详情:');
      testResults.errors.forEach(err => console.log(`  - ${err}`));
    }

    console.log('\n最终结果:');
    if (testResults.success) {
      console.log('🎉 所有测试通过！修复验证成功！');
    } else {
      console.log('❌ 测试存在失败项');
    }

    const screenshotPath = '/workspace/bk-cmdb/cmdb_ui_lite/slb-id1-test-result.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`\n截图已保存: ${screenshotPath}`);

  } catch (error) {
    console.error('\n❌ 测试执行出错:', error.message);
    testResults.errors.push(error.message);
    testResults.success = false;

    try {
      await page.screenshot({ path: '/workspace/bk-cmdb/cmdb_ui_lite/slb-id1-test-error.png' });
      console.log('错误截图已保存');
    } catch (e) {
      console.log('无法保存截图');
    }
  } finally {
    await browser.close();
  }

  console.log('\n' + '='.repeat(60));
  console.log('详细测试结果:');
  console.log('='.repeat(60));
  console.log(JSON.stringify(testResults, null, 2));

  process.exit(testResults.success ? 0 : 1);
})();
