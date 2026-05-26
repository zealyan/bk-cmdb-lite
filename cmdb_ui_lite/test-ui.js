const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    console.log('=== UI自动化测试开始 ===\n');

    console.log('1. 打开页面...');
    await page.goto('http://localhost:36081/');
    await page.waitForLoadState('networkidle');

    console.log('\n2. 导航到SLB实例详情页 (instId=1)...');
    await page.goto('http://localhost:36081/#/instance/bk_slb/1');
    await page.waitForTimeout(1500);

    console.log('\n3. 检查详情页内容...');
    const detailsText = await page.textContent('body');
    console.log('   页面包含"基本信息":', detailsText.includes('基本信息'));
    console.log('   页面包含"关联":', detailsText.includes('关联'));

    if (detailsText.includes('关联')) {
      console.log('\n4. 点击"关联"tab...');
      await page.click('.bk-tab-label-item:has-text("关联"), [role="tab"]:has-text("关联")');
      await page.waitForTimeout(1000);
      
      const assocContent = await page.textContent('body');
      console.log('   页面包含"SLB后端服务器":', assocContent.includes('SLB后端服务器'));
      console.log('   页面包含"SLB监听器":', assocContent.includes('SLB监听器'));

      console.log('\n5. 等待并查找分组元素...');
      await page.waitForSelector('.group-info', { state: 'visible', timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(500);

      console.log('\n6. 检查Vue组件状态...');
      const vueDataBefore = await page.evaluate(() => {
        const el = document.querySelector('.instance-association');
        if (el && el.__vue__) {
          return {
            expandedKeys: { ...el.__vue__.expandedKeys }
          };
        }
        return null;
      });
      console.log('   点击前Vue state:', vueDataBefore);

      console.log('\n7. 测试第一个分组的折叠功能...');
      const iconBefore = await page.$eval('.group-info .icon-right-shape', el => el.className);
      console.log('   折叠前图标class:', iconBefore);
      
      console.log('\n   触发点击...');
      await page.evaluate(() => {
        const groupInfo = document.querySelector('.group-info');
        if (groupInfo) {
          const event = new MouseEvent('click', {
            bubbles: true,
            cancelable: true,
            view: window
          });
          groupInfo.dispatchEvent(event);
        }
      });
      await page.waitForTimeout(500);

      const iconAfter = await page.$eval('.group-info .icon-right-shape', el => el.className);
      console.log('   折叠后图标class:', iconAfter);

      const vueDataAfter = await page.evaluate(() => {
        const el = document.querySelector('.instance-association');
        if (el && el.__vue__) {
          return {
            expandedKeys: { ...el.__vue__.expandedKeys }
          };
        }
        return null;
      });
      console.log('   折叠后Vue state:', vueDataAfter);

      console.log('\n=== 折叠功能测试结果 ===');
      if (iconBefore.includes('is-open') && !iconAfter.includes('is-open')) {
        console.log('   ✅ 折叠功能正常: 展开 -> 合起');
      } else if (!iconBefore.includes('is-open') && iconAfter.includes('is-open')) {
        console.log('   ✅ 折叠功能正常: 合起 -> 展开');
      } else if (iconBefore === iconAfter) {
        console.log('   ⚠️  折叠状态未改变');
      }

      console.log('\n8. 测试恢复展开...');
      await page.evaluate(() => {
        const groupInfo = document.querySelector('.group-info');
        if (groupInfo) {
          groupInfo.click();
        }
      });
      await page.waitForTimeout(500);
      const iconFinal = await page.$eval('.group-info .icon-right-shape', el => el.className);
      console.log('   最终图标class:', iconFinal);
      if (iconFinal.includes('is-open')) {
        console.log('   ✅ 恢复展开功能正常');
      }
    }

    console.log('\n=== 测试完成 ===');

  } catch (error) {
    console.error('\n测试过程中出错:', error.message);
    try {
      await page.screenshot({ path: '/workspace/bk-cmdb/cmdb_ui_lite/error-screenshot.png' });
      console.log('截图已保存到: /workspace/bk-cmdb/cmdb_ui_lite/error-screenshot.png');
    } catch (e) {}
  } finally {
    await browser.close();
  }
})();
